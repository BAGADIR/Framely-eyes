"""Simplified optical flow motion validation.
If heavy flow is not available, return a light motion score.
"""
from typing import Dict, Any
import numpy as np
import cv2

from services.utils.hashing import sha256_obj


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a lightweight motion score using frame differencing.

    Args:
        shot: Shot metadata containing frame paths
        cfg: Configuration

    Returns:
        Dict containing flow map summary and motion_score
    """
    frame_paths = shot.get("frame_paths", [])
    if len(frame_paths) < 2:
        return {"flow": None, "motion_score": 0.0, "provenance": {}}

    # Read first and last frame as a proxy for motion amount
    first = cv2.imread(frame_paths[0])
    last = cv2.imread(frame_paths[-1])
    if first is None or last is None:
        return {"flow": None, "motion_score": 0.0, "provenance": {}}

    first_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
    last_gray = cv2.cvtColor(last, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(first_gray, last_gray)
    score = float(np.mean(diff) / 255.0)

    params = {"method": "frame_diff"}
    provenance = {
        "tool": "optical_flow",
        "version": "0.1",
        "ckpt": None,
        "params_hash": sha256_obj(params),
    }
    return {"flow": None, "motion_score": score, "provenance": provenance}
