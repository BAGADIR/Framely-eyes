"""Main orchestrator for video analysis DAG execution."""
import asyncio
import yaml
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.detectors import (
    prep, yolo, tile_yolo, sam2, superres, faces,
    ocr_fonts, color_comp, motion_saliency, audio_eng, transitions
)
from services.orchestrator.gpu_pool import get_gpu_pool
from services.orchestrator.dag_types import DetectorStage, DetectorDAG
from services.utils.io import save_vab, get_frames_dir
from services.utils.merge import build_scenes, assemble_vab
from services.utils.coverage import compute_coverage, enforce_gates
from services.utils.hashing import sha256_file
from services.observability.metrics import METRICS, vram_peak, timed
from services.qwen.vl_client import analyze_shot as qwen_analyze_shot, analyze_scene


# Load configuration
CFG = yaml.safe_load(open("configs/limits.yaml"))


def _apply_ablation(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Apply ablation flags to disable certain features.
    
    Args:
        cfg: Configuration dict
        
    Returns:
        Modified configuration
    """
    ab = cfg.get("ablation", {})
    if ab.get("no_sr"):
        cfg["detect"]["superres"]["enabled"] = False
    if ab.get("no_tiling"):
        cfg["detect"]["two_pass"]["enabled"] = False
    if ab.get("light_audio"):
        cfg["audio"]["stoi"]["enabled"] = False
    return cfg


async def analyze_shot_safe(
    meta: Dict[str, Any],
    shot: Dict[str, Any],
    cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze a single shot with OOM safety and fallback.
    
    Args:
        meta: Video metadata
        shot: Shot metadata
        cfg: Configuration dict
        
    Returns:
        Shot analysis bundle
    """
    gpu_pool = get_gpu_pool(cfg["runtime"]["gpu_semaphore"])
    
    try:
        return await analyze_shot(meta, shot, cfg, gpu_pool)
    except RuntimeError as e:
        if "CUDA out of memory" in str(e) or "out of memory" in str(e).lower():
            METRICS["oom_trips"] += 1
            
            # Apply fallback ladder
            for step in cfg["runtime"]["oom_fallback_order"]:
                if step == "sam2_off":
                    if "flags" not in shot:
                        shot["flags"] = []
                    shot["flags"].append("sam2_off")
                    shot["sam2_disabled"] = True
                elif step == "sr_off":
                    if "flags" not in shot:
                        shot["flags"] = []
                    shot["flags"].append("sr_off")
                    cfg["detect"]["superres"]["enabled"] = False
                elif step == "qwen_ctx_shrink":
                    shot["qwen_ctx"] = max(6, cfg["runtime"]["qwen_context_max_frames"] // 2)
            
            # Retry once with fallbacks
            return await analyze_shot(meta, shot, cfg, gpu_pool)
        raise


async def analyze_shot(
    meta: Dict[str, Any],
    shot: Dict[str, Any],
    cfg: Dict[str, Any],
    gpu_pool: Any
) -> Dict[str, Any]:
    """Analyze a single shot through detector DAG.
    
    Args:
        meta: Video metadata
        shot: Shot metadata
        cfg: Configuration dict
        gpu_pool: GPU resource pool
        
    Returns:
        Complete shot analysis bundle
    """
    # Prepare frame paths for this shot
    frames_dir = get_frames_dir(meta["video_id"])
    frame_paths = []
    for i in range(shot["start_frame"], shot["end_frame"] + 1):
        frame_path = os.path.join(frames_dir, f"frame_{i:08d}.jpg")
        if os.path.exists(frame_path):
            frame_paths.append(frame_path)
    
    shot["frame_paths"] = frame_paths
    shot["fps"] = meta["fps"]
    
    # Initialize detectors dict
    detectors = {}
    
    # Phase 1: GPU-heavy object detection pipeline
    async with gpu_pool:
        # YOLO coarse
        yolo_result = yolo.detect(shot, cfg)
        detectors["objects_coarse"] = yolo_result.get("objects", [])
        
        # YOLO tiled (if enabled)
        if cfg["detect"]["two_pass"]["enabled"]:
            tile_result = tile_yolo.detect(shot, cfg)
            detectors["objects"] = tile_result.get("objects", [])
        else:
            detectors["objects"] = detectors["objects_coarse"]
        
        # Super-resolution (if needed)
        sr_result = superres.detect(shot, cfg)
        detectors["sr_used"] = sr_result.get("sr_used", False)
        
        # SAM2 refinement (if not disabled)
        if not shot.get("sam2_disabled", False):
            shot_with_objects = {**shot, "detectors": {"objects": detectors["objects"]}}
            sam2_result = sam2.detect(shot_with_objects, cfg)
            detectors["objects"] = sam2_result.get("objects", detectors["objects"])
        
        # Faces
        face_result = faces.detect(shot, cfg)
        detectors["faces"] = face_result.get("faces", [])
    
    # Phase 2: CPU detectors (can run in parallel)
    cpu_tasks = [
        ocr_fonts.detect(shot, cfg),
        color_comp.detect(shot, cfg),
        motion_saliency.detect(shot, cfg),
        transitions.detect(shot, cfg)
    ]
    
    cpu_results = await asyncio.gather(*cpu_tasks)
    detectors["text"] = cpu_results[0].get("text", [])
    detectors["color"] = cpu_results[1].get("color", {})
    detectors["motion"] = cpu_results[2].get("motion", {})
    detectors["saliency"] = cpu_results[2].get("saliency", {})
    detectors["transition"] = cpu_results[3].get("transition", {})
    
    # Phase 3: Audio analysis
    audio_path = meta.get("audio_path")
    if audio_path:
        audio_result = audio_eng.detect(shot, cfg, audio_path)
        detectors["audio"] = audio_result.get("audio", {})
    
    # Phase 4: Qwen VL reasoning
    async with gpu_pool:
        qwen_ctx_frames = shot.get("qwen_ctx", cfg["runtime"]["qwen_context_max_frames"])
        shot_bundle = {
            **shot,
            "detectors": detectors
        }
        qwen_result = await qwen_analyze_shot(shot_bundle, frame_paths[:qwen_ctx_frames])
        shot_bundle.update(qwen_result)
    
    return shot_bundle


@timed("run_analysis")
async def run_analysis(
    video_id: str,
    media_url: Optional[str] = None,
    ablations: Optional[Dict[str, bool]] = None
) -> str:
    """Run complete video analysis pipeline.
    
    Args:
        video_id: Unique video identifier
        media_url: URL to video file (optional)
        ablations: Optional ablation flags
        
    Returns:
        Job ID
    """
    # Apply configuration
    cfg = CFG.copy()
    if ablations:
        cfg["ablation"].update(ablations)
    cfg = _apply_ablation(cfg)
    
    # Preparation phase
    print(f"[{video_id}] Starting preparation...")
    meta = prep.prepare(video_id, media_url, cfg)
    video_sha = sha256_file(meta["path"])
    meta["sha256"] = video_sha
    
    provenance = [{
        "tool": "ingest",
        "version": "0.2.1",
        "params_hash": video_sha,
        "ts": datetime.utcnow().isoformat()
    }]
    
    # Analyze all shots in parallel
    print(f"[{video_id}] Analyzing {len(meta['shots'])} shots...")
    tasks = [analyze_shot_safe(meta, shot, cfg) for shot in meta["shots"]]
    shot_bundles = await asyncio.gather(*tasks)
    
    # Build scenes
    print(f"[{video_id}] Building scenes...")
    scenes = build_scenes(shot_bundles, meta, cfg)
    
    # Scene-level Qwen reasoning
    print(f"[{video_id}] Analyzing {len(scenes)} scenes...")
    for scene in scenes:
        scene_shots = [s for s in shot_bundles if s["shot_id"] in scene["shots"]]
        scene["narrative"] = await analyze_scene(scene, scene_shots)
    
    # Coverage computation
    print(f"[{video_id}] Computing coverage metrics...")
    audio_report = audio_eng.global_report(meta)
    coverage = compute_coverage(meta, shot_bundles, audio_report, cfg)
    state, reasons = enforce_gates(coverage, cfg)
    
    # Risk detection
    risks = []
    for s in shot_bundles:
        audio_data = s.get("detectors", {}).get("audio", {})
        dialogue = audio_data.get("dialogue", {})
        
        if dialogue.get("stoi", 1.0) < cfg["audio"]["stoi"]["min_ok"]:
            risks.append({
                "shot_id": s["shot_id"],
                "type": "low_dialogue_intelligibility",
                "metric": {"stoi": dialogue["stoi"]},
                "severity": "high"
            })
        
        if s.get("flags") and "sam2_off" in s["flags"]:
            risks.append({
                "shot_id": s["shot_id"],
                "type": "sam2_disabled",
                "severity": "medium"
            })
    
    # Assemble VAB
    print(f"[{video_id}] Assembling VAB...")
    vab = assemble_vab(meta, scenes, shot_bundles)
    vab["schema_version"] = "1.1.0"
    vab["status"] = {
        "state": state,
        "reasons": reasons,
        "coverage": coverage
    }
    vab["risks"] = risks
    vab["provenance"] = provenance
    vab["calibration"] = [
        {"family": "objects", "expected_tpr": 0.94, "expected_fpr": 0.06},
        {"family": "ocr", "expected_tpr": 0.97, "expected_fpr": 0.03},
        {"family": "audio", "expected_tpr": 0.98, "expected_fpr": 0.02}
    ]
    
    # Add metrics
    vram_peak()
    vab["video"]["metrics"] = METRICS.copy()
    
    # Save VAB
    vab_path = save_vab(video_id, vab)
    print(f"[{video_id}] Analysis complete. VAB saved to {vab_path}")
    
    return f"job_{video_id}"
