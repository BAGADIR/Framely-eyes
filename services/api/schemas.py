"""Pydantic schemas for Framely-Eyes API and VAB structure."""
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Optional, Any
from datetime import datetime


class Provenance(BaseModel):
    """Provenance information for analysis tools."""
    tool: str
    version: str
    ckpt: Optional[str] = None
    params_hash: Optional[str] = None
    seed: Optional[int] = None
    ts: Optional[str] = None


class Calibration(BaseModel):
    """Calibration metrics for detector families."""
    family: str  # e.g., "objects", "faces", "ocr", "audio"
    expected_tpr: float  # True positive rate
    expected_fpr: float  # False positive rate
    notes: Optional[str] = None


class Coverage(BaseModel):
    """Coverage metrics for video analysis."""
    spatial: Dict[str, Any]
    temporal: Dict[str, Any]
    audio: Dict[str, Any]


class Status(BaseModel):
    """Analysis status with quality gates."""
    state: str  # "ok" | "degraded" | "failed"
    reasons: List[str] = []
    coverage: Coverage


class Risk(BaseModel):
    """Risk or issue detected in analysis."""
    shot_id: Optional[str] = None
    scene_id: Optional[str] = None
    type: str
    severity: str  # "low" | "medium" | "high"
    metric: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class VideoMetadata(BaseModel):
    """Video file metadata."""
    video_id: str
    path: str
    sha256: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class GlobalStats(BaseModel):
    """Global video statistics."""
    total_frames: int
    duration_s: float
    fps: float
    resolution: Dict[str, int]
    detections: Dict[str, Any]


class VAB(BaseModel):
    """Video Analysis Bundle - complete structured output."""
    schema_version: str = "1.1.0"
    status: Status
    video: VideoMetadata
    global_: GlobalStats = Field(alias="global")
    scenes: List[Dict[str, Any]]
    shots: List[Dict[str, Any]]
    tracks: List[Dict[str, Any]] = []
    risks: List[Risk] = []
    provenance: List[Provenance] = []
    calibration: List[Calibration] = []
    
    class Config:
        populate_by_name = True


# API Request/Response Models

class AnalyzeRequest(BaseModel):
    """Request to analyze a video."""
    video_id: str
    media_url: Optional[HttpUrl] = None
    ablations: Optional[Dict[str, bool]] = None


class AnalyzeResponse(BaseModel):
    """Response from analyze endpoint."""
    job_id: str
    video_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    video_id: str
    state: str  # "queued" | "processing" | "completed" | "failed"
    progress: Optional[float] = None
    message: Optional[str] = None
    vab_available: bool = False


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    gpu_available: bool
    redis_connected: bool
    qwen_available: bool
