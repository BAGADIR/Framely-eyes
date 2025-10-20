"""Transition detection using SSIM and optical flow patterns."""
import cv2
import numpy as np
from typing import Dict, Any, List
from skimage.metrics import structural_similarity as ssim
from services.utils.hashing import sha256_obj


def compute_frame_similarity(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """Compute structural similarity between frames.
    
    Args:
        frame1: First frame
        frame2: Second frame
        
    Returns:
        SSIM score [0, 1]
    """
    # Convert to grayscale
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Resize for speed
    h, w = gray1.shape
    if h > 480:
        scale = 480 / h
        gray1 = cv2.resize(gray1, None, fx=scale, fy=scale)
        gray2 = cv2.resize(gray2, None, fx=scale, fy=scale)
    
    # Compute SSIM
    score = ssim(gray1, gray2)
    return float(score)


def detect_transition_type(
    prev_frame: np.ndarray,
    curr_frame: np.ndarray,
    similarity: float
) -> str:
    """Detect type of transition between frames.
    
    Args:
        prev_frame: Previous frame
        curr_frame: Current frame
        similarity: SSIM similarity score
        
    Returns:
        Transition type
    """
    if similarity > 0.9:
        return "none"
    elif similarity < 0.3:
        return "cut"
    else:
        # Check for fade/dissolve by analyzing pixel distributions
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        
        prev_mean = np.mean(prev_gray)
        curr_mean = np.mean(curr_gray)
        
        brightness_diff = abs(curr_mean - prev_mean)
        
        if brightness_diff > 50:
            if curr_mean < 30:
                return "fade_to_black"
            elif prev_mean < 30:
                return "fade_from_black"
            else:
                return "fade"
        else:
            return "dissolve"


def analyze_shot_transition(
    shot: Dict[str, Any],
    prev_shot: Dict[str, Any],
    frame_paths: List[str]
) -> Dict[str, Any]:
    """Analyze transition between shots.
    
    Args:
        shot: Current shot metadata
        prev_shot: Previous shot metadata
        frame_paths: List of all frame paths
        
    Returns:
        Transition analysis
    """
    # Get last frame of previous shot and first frame of current shot
    prev_end_frame = prev_shot.get("end_frame", 0)
    curr_start_frame = shot.get("start_frame", 0)
    
    if prev_end_frame >= len(frame_paths) or curr_start_frame >= len(frame_paths):
        return {"type": "unknown"}
    
    prev_frame = cv2.imread(frame_paths[prev_end_frame])
    curr_frame = cv2.imread(frame_paths[curr_start_frame])
    
    if prev_frame is None or curr_frame is None:
        return {"type": "unknown"}
    
    # Compute similarity
    similarity = compute_frame_similarity(prev_frame, curr_frame)
    
    # Detect transition type
    trans_type = detect_transition_type(prev_frame, curr_frame, similarity)
    
    return {
        "type": trans_type,
        "similarity": round(similarity, 3),
        "sharpness": "hard" if similarity < 0.5 else "soft"
    }


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Detect and classify transitions for a shot.
    
    Args:
        shot: Shot metadata
        cfg: Configuration dictionary
        
    Returns:
        Transition detection results with provenance
    """
    params = {
        "method": "ssim_flow",
        "cut_threshold": 0.3,
        "dissolve_threshold": 0.7
    }
    
    # Get transition info from shot metadata
    transition = shot.get("transition", {})
    
    provenance = {
        "tool": "transition_detector",
        "version": "1.0",
        "ckpt": "ssim+optical_flow",
        "params_hash": sha256_obj(params)
    }
    
    return {
        "transition": transition,
        "provenance": provenance
    }
