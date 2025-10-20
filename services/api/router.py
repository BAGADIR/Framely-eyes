"""API routes for Framely-Eyes analyzer."""
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import magic

from services.api.schemas import (
    AnalyzeRequest, AnalyzeResponse, JobStatus, HealthResponse
)
from services.api.deps import settings, get_redis, check_gpu_available, check_redis_connected, check_qwen_available
from services.orchestrator.orchestrator import run_analysis
from services.utils.io import load_vab


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.
    
    Returns:
        Health status
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        gpu_available=check_gpu_available(),
        redis_connected=check_redis_connected(),
        qwen_available=check_qwen_available()
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest):
    """Start video analysis job.
    
    Args:
        request: Analysis request
        
    Returns:
        Job status
    """
    video_id = request.video_id
    media_url = str(request.media_url) if request.media_url else None
    ablations = request.ablations
    
    # Store job in Redis
    redis_client = get_redis()
    job_key = f"job:{video_id}"
    redis_client.hset(job_key, mapping={
        "video_id": video_id,
        "state": "queued",
        "created_at": datetime.utcnow().isoformat()
    })
    
    # Start analysis in background
    asyncio.create_task(run_analysis_task(video_id, media_url, ablations))
    
    return AnalyzeResponse(
        job_id=f"job_{video_id}",
        video_id=video_id,
        status="queued",
        message="Analysis job queued"
    )


@router.post("/ingest")
async def ingest_video(
    video_id: str = Form(...),
    file: UploadFile = File(None),
    url: Optional[str] = Form(None)
):
    """Ingest video file or URL.
    
    Args:
        video_id: Unique video identifier
        file: Video file upload
        url: Video URL
        
    Returns:
        Ingestion status
    """
    if not file and not url:
        raise HTTPException(400, "Either file or url must be provided")
    
    # Check file size
    if file and file.size and file.size > settings.MAX_VIDEO_MB * 1024 * 1024:
        raise HTTPException(413, "File too large")
    
    # Check MIME type
    if file:
        content = await file.read(1024)
        await file.seek(0)
        mime = magic.from_buffer(content, mime=True)
        
        if mime not in settings.MIME_WHITELIST:
            raise HTTPException(415, f"Unsupported media type: {mime}")
        
        # Save file
        import os
        from services.utils.io import get_video_dir
        video_dir = get_video_dir(video_id, settings.STORE_PATH)
        video_path = os.path.join(video_dir, "video.mp4")
        
        with open(video_path, 'wb') as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                f.write(chunk)
        
        return {"status": "success", "video_id": video_id, "path": video_path}
    
    return {"status": "success", "video_id": video_id, "url": url}


@router.get("/result/{video_id}")
async def get_result(video_id: str):
    """Get analysis result (VAB).
    
    Args:
        video_id: Video identifier
        
    Returns:
        VAB JSON or status
    """
    # Check job status
    redis_client = get_redis()
    job_key = f"job:{video_id}"
    job_data = redis_client.hgetall(job_key)
    
    if not job_data:
        raise HTTPException(404, "Job not found")
    
    state = job_data.get("state", "unknown")
    
    if state == "completed":
        # Load VAB
        vab = load_vab(video_id, settings.STORE_PATH)
        if vab:
            return JSONResponse(content=vab)
        else:
            raise HTTPException(404, "VAB not found")
    
    elif state == "failed":
        return {
            "status": "failed",
            "error": job_data.get("error", "Unknown error")
        }
    
    else:
        return {
            "status": state,
            "progress": float(job_data.get("progress", 0))
        }


@router.get("/status/{video_id}", response_model=JobStatus)
async def get_status(video_id: str):
    """Get job status.
    
    Args:
        video_id: Video identifier
        
    Returns:
        Job status
    """
    redis_client = get_redis()
    job_key = f"job:{video_id}"
    job_data = redis_client.hgetall(job_key)
    
    if not job_data:
        raise HTTPException(404, "Job not found")
    
    state = job_data.get("state", "unknown")
    progress = float(job_data.get("progress", 0))
    
    # Check if VAB exists
    vab_available = False
    if state == "completed":
        vab = load_vab(video_id, settings.STORE_PATH)
        vab_available = vab is not None
    
    return JobStatus(
        job_id=f"job_{video_id}",
        video_id=video_id,
        state=state,
        progress=progress,
        message=job_data.get("message"),
        vab_available=vab_available
    )


async def run_analysis_task(
    video_id: str,
    media_url: Optional[str],
    ablations: Optional[dict]
):
    """Background task to run analysis.
    
    Args:
        video_id: Video identifier
        media_url: Video URL
        ablations: Ablation flags
    """
    redis_client = get_redis()
    job_key = f"job:{video_id}"
    
    try:
        # Update status
        redis_client.hset(job_key, "state", "processing")
        redis_client.hset(job_key, "started_at", datetime.utcnow().isoformat())
        
        # Run analysis
        job_id = await run_analysis(video_id, media_url, ablations)
        
        # Update status
        redis_client.hset(job_key, "state", "completed")
        redis_client.hset(job_key, "completed_at", datetime.utcnow().isoformat())
        redis_client.hset(job_key, "progress", "100")
        
    except Exception as e:
        # Update status
        redis_client.hset(job_key, "state", "failed")
        redis_client.hset(job_key, "error", str(e))
        redis_client.hset(job_key, "failed_at", datetime.utcnow().isoformat())
        print(f"Analysis failed for {video_id}: {e}")
