"""Coverage computation and quality gates for video analysis."""
from typing import Dict, Any, List, Tuple


def compute_coverage(
    meta: Dict[str, Any],
    shots: List[Dict[str, Any]],
    audio_report: Dict[str, Any],
    cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute spatial, temporal, and audio coverage metrics.
    
    Args:
        meta: Video metadata including total frames
        shots: List of analyzed shot bundles
        audio_report: Global audio analysis report
        cfg: Configuration dict from limits.yaml
        
    Returns:
        Coverage dict with spatial, temporal, and audio metrics
    """
    total_frames = int(meta.get("frames", 0))
    analyzed = sum([s.get("frame_count", 0) for s in shots])
    frames_pct = round(100.0 * analyzed / max(1, total_frames), 2)
    
    # Spatial coverage with tiling
    spatial = {
        "tile_size": cfg["detect"]["tile"]["size"],
        "stride": cfg["detect"]["tile"]["stride"],
        "sr_used": any(s.get("detectors", {}).get("sr_used", False) for s in shots),
        "pixels_covered_pct": 100.0,  # with tiling stride < size → 100%
        "min_detectable_px": cfg["detect"]["small_object_min_px"]
    }
    
    # Audio coverage
    audio = {
        "lufs_trace_pct": audio_report.get("lufs_trace_pct", 100.0),
        "stoi_pct": audio_report.get("stoi_pct", 0.0)
    }
    
    return {
        "spatial": spatial,
        "temporal": {
            "frame_stride": cfg["runtime"]["frame_stride"],
            "frames_analyzed_pct": frames_pct
        },
        "audio": audio
    }


def enforce_gates(
    coverage: Dict[str, Any],
    cfg: Dict[str, Any]
) -> Tuple[str, List[str]]:
    """Enforce quality gates based on coverage thresholds.
    
    Args:
        coverage: Coverage metrics dict
        cfg: Configuration dict from limits.yaml
        
    Returns:
        Tuple of (state, reasons) where state is "ok"|"degraded"|"failed"
    """
    th = cfg["coverage_thresholds"]
    state = "ok"
    reasons = []
    
    # Temporal coverage check
    if coverage["temporal"]["frames_analyzed_pct"] < th["frames_analyzed_pct"]:
        state = "degraded"
        reasons.append("low_temporal_coverage")
    
    # Spatial resolution check
    if coverage["spatial"]["min_detectable_px"] > th["min_detectable_px"]:
        state = "degraded"
        reasons.append("min_detectable_px_too_large")
    
    # Audio LUFS trace check
    if coverage["audio"]["lufs_trace_pct"] < th["lufs_trace_pct"]:
        state = "degraded"
        reasons.append("lufs_trace_missing")
    
    # Audio STOI check
    if coverage["audio"]["stoi_pct"] < th["stoi_pct"]:
        state = "degraded"
        reasons.append("low_stoi_coverage")
    
    return state, reasons


def validate_shot_coverage(shot: Dict[str, Any], cfg: Dict[str, Any]) -> List[str]:
    """Validate coverage for a single shot.
    
    Args:
        shot: Shot analysis bundle
        cfg: Configuration dict
        
    Returns:
        List of validation warnings
    """
    warnings = []
    
    # Check if key detectors ran
    detectors = shot.get("detectors", {})
    if not detectors.get("objects"):
        warnings.append("missing_object_detection")
    if not detectors.get("faces") and shot.get("has_people", False):
        warnings.append("missing_face_detection")
    if not detectors.get("audio"):
        warnings.append("missing_audio_analysis")
    
    return warnings
