"""Production optical flow using Farneback dense flow.

Computes motion vectors, magnitude, and direction for motion validation.
Supports per-object motion validation and camera motion detection.
"""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import cv2

from services.utils.hashing import sha256_obj


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Compute dense optical flow using Farneback algorithm.

    Args:
        shot: Shot metadata with:
            - frame_paths: List of frame file paths
            - detectors.objects: Optional list of detected objects for per-object flow
        
        cfg: Configuration dictionary (currently unused, reserved for future params)

    Returns:
        Dict with:
            - flow: Flow statistics (magnitude, direction, distribution)
            - motion_score: Overall motion score [0.0-1.0]
            - per_object_motion: Optional per-object motion validation
            - provenance: Processing metadata
    """
    frame_paths = shot.get("frame_paths", [])
    if len(frame_paths) < 2:
        return {
            "flow": None,
            "motion_score": 0.0,
            "provenance": _build_provenance("no_frames")
        }

    # Sample frames for flow computation
    # For shots >30 frames, sample every Nth frame to avoid processing all pairs
    sampled_pairs = _sample_frame_pairs(frame_paths, max_pairs=10)
    
    if not sampled_pairs:
        return {
            "flow": None,
            "motion_score": 0.0,
            "provenance": _build_provenance("sampling_failed")
        }

    # Compute flow for each pair and aggregate
    flow_results = []
    for prev_path, curr_path in sampled_pairs:
        flow_data = _compute_flow_pair(prev_path, curr_path)
        if flow_data is not None:
            flow_results.append(flow_data)
    
    if not flow_results:
        return {
            "flow": None,
            "motion_score": 0.0,
            "provenance": _build_provenance("computation_failed")
        }

    # Aggregate flow statistics
    aggregated = _aggregate_flow_stats(flow_results)
    
    # Compute per-object motion if objects are available
    objects = shot.get("detectors", {}).get("objects", [])
    per_object_motion = None
    if objects and flow_results:
        per_object_motion = _compute_per_object_motion(objects, flow_results[0])

    return {
        "flow": aggregated,
        "motion_score": aggregated["mean_magnitude"],
        "per_object_motion": per_object_motion,
        "provenance": _build_provenance("farneback")
    }


def _sample_frame_pairs(
    frame_paths: List[str],
    max_pairs: int = 10
) -> List[Tuple[str, str]]:
    """Sample frame pairs for flow computation.
    
    Args:
        frame_paths: List of all frame paths
        max_pairs: Maximum number of pairs to sample
    
    Returns:
        List of (prev_frame, curr_frame) path tuples
    """
    n_frames = len(frame_paths)
    if n_frames < 2:
        return []
    
    # For short shots, use all consecutive pairs
    if n_frames <= max_pairs + 1:
        return [(frame_paths[i], frame_paths[i+1]) for i in range(n_frames - 1)]
    
    # For long shots, sample evenly
    step = (n_frames - 1) / max_pairs
    pairs = []
    for i in range(max_pairs):
        idx = int(i * step)
        if idx + 1 < n_frames:
            pairs.append((frame_paths[idx], frame_paths[idx + 1]))
    
    return pairs


def _compute_flow_pair(prev_path: str, curr_path: str) -> Optional[Dict[str, Any]]:
    """Compute optical flow between two frames.
    
    Args:
        prev_path: Path to previous frame
        curr_path: Path to current frame
    
    Returns:
        Dict with flow vectors, magnitude, angle, or None if failed
    """
    prev = cv2.imread(prev_path, cv2.IMREAD_GRAYSCALE)
    curr = cv2.imread(curr_path, cv2.IMREAD_GRAYSCALE)
    
    if prev is None or curr is None:
        return None
    
    # Resize for faster computation if very large
    h, w = prev.shape
    if h > 720 or w > 1280:
        scale = min(720 / h, 1280 / w)
        new_h, new_w = int(h * scale), int(w * scale)
        prev = cv2.resize(prev, (new_w, new_h))
        curr = cv2.resize(curr, (new_w, new_h))
    
    # Compute dense optical flow using Farneback algorithm
    flow = cv2.calcOpticalFlowFarneback(
        prev, curr,
        flow=None,
        pyr_scale=0.5,      # Pyramid scale
        levels=3,           # Number of pyramid levels
        winsize=15,         # Averaging window size
        iterations=3,       # Iterations at each level
        poly_n=5,          # Polynomial expansion size
        poly_sigma=1.2,    # Gaussian std for polynomial expansion
        flags=0
    )
    
    # Convert flow to polar coordinates (magnitude and angle)
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    
    return {
        "magnitude": magnitude,
        "angle": angle,
        "flow": flow,
        "shape": prev.shape
    }


def _aggregate_flow_stats(flow_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate flow statistics across multiple frame pairs.
    
    Args:
        flow_results: List of flow computation results
    
    Returns:
        Aggregated flow statistics
    """
    all_magnitudes = []
    all_angles = []
    
    for result in flow_results:
        mag = result["magnitude"].flatten()
        ang = result["angle"].flatten()
        
        # Filter out very low motion (noise)
        valid_mask = mag > 0.5
        all_magnitudes.extend(mag[valid_mask].tolist())
        all_angles.extend(ang[valid_mask].tolist())
    
    if not all_magnitudes:
        return {
            "mean_magnitude": 0.0,
            "max_magnitude": 0.0,
            "dominant_direction_deg": 0.0,
            "motion_distribution": "static"
        }
    
    mag_array = np.array(all_magnitudes)
    ang_array = np.array(all_angles)
    
    # Compute statistics
    mean_mag = float(np.mean(mag_array))
    max_mag = float(np.max(mag_array))
    
    # Dominant direction (circular mean for angles)
    dominant_dir = float(np.mean(ang_array) * 180 / np.pi)
    
    # Motion distribution classification
    motion_std = float(np.std(mag_array))
    if mean_mag < 1.0:
        distribution = "static"
    elif motion_std / (mean_mag + 1e-6) < 0.3:
        distribution = "uniform"  # Camera pan/tilt
    else:
        distribution = "localized"  # Object motion
    
    return {
        "mean_magnitude": min(mean_mag / 10.0, 1.0),  # Normalize to [0, 1]
        "max_magnitude": min(max_mag / 10.0, 1.0),
        "dominant_direction_deg": dominant_dir,
        "motion_distribution": distribution,
        "motion_std": motion_std
    }


def _compute_per_object_motion(
    objects: List[Dict[str, Any]],
    flow_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Compute motion statistics for each detected object.
    
    Args:
        objects: List of detected objects with bboxes
        flow_data: Flow computation result with magnitude/angle
    
    Returns:
        List of per-object motion statistics
    """
    magnitude = flow_data["magnitude"]
    angle = flow_data["angle"]
    h, w = flow_data["shape"]
    
    per_object = []
    
    for obj in objects:
        bbox = obj.get("bbox", [])
        if len(bbox) != 4:
            per_object.append({"motion_magnitude": 0.0, "valid": False})
            continue
        
        # Extract region from flow
        x, y, bw, bh = bbox
        x1, y1 = int(x), int(y)
        x2, y2 = int(x + bw), int(y + bh)
        
        # Clip to image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            per_object.append({"motion_magnitude": 0.0, "valid": False})
            continue
        
        # Compute mean motion in bbox region
        region_mag = magnitude[y1:y2, x1:x2]
        region_ang = angle[y1:y2, x1:x2]
        
        obj_motion = {
            "motion_magnitude": float(np.mean(region_mag)),
            "motion_direction_deg": float(np.mean(region_ang) * 180 / np.pi),
            "motion_std": float(np.std(region_mag)),
            "valid": True
        }
        
        per_object.append(obj_motion)
    
    return per_object


def _build_provenance(status: str) -> Dict[str, Any]:
    """Build provenance metadata for optical flow.
    
    Args:
        status: Processing status or method used
    
    Returns:
        Provenance dictionary
    """
    params = {
        "method": "farneback",
        "pyr_scale": 0.5,
        "levels": 3,
        "winsize": 15,
        "status": status
    }
    
    return {
        "tool": "optical_flow",
        "version": "1.0.0",
        "ckpt": None,
        "params_hash": sha256_obj(params),
    }
