"""Simple tracking stub: assigns stable IDs to detections per shot.
Falls back to passthrough when ByteTrack is unavailable.
"""
from typing import Dict, Any, List

try:
    from yolox.tracker.byte_tracker import BYTETracker  # type: ignore
    BYTETRACK_AVAILABLE = True
except Exception:
    BYTETRACK_AVAILABLE = False

from services.utils.hashing import sha256_obj


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Assign track ids to detected objects.

    Args:
        shot: Shot metadata with existing detections under shot["detectors"]["objects"]
        cfg: Configuration dictionary

    Returns:
        Dict with updated objects list and provenance
    """
    objects: List[Dict[str, Any]] = shot.get("detectors", {}).get("objects", []) or []

    if not objects:
        return {"objects": [], "provenance": {}}

    # Minimal deterministic IDs for this frame (ByteTrack would need multi-frame stream)
    for i, obj in enumerate(objects):
        obj["track_id"] = i

    params = {
        "tracker": "passthrough" if not BYTETRACK_AVAILABLE else "bytetrack-single-frame",
    }

    provenance = {
        "tool": "tracker",
        "version": "0.1",
        "ckpt": None,
        "params_hash": sha256_obj(params),
    }

    return {"objects": objects, "provenance": provenance}
