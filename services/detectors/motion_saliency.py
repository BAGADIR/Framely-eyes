"""Motion detection and saliency analysis using optical flow."""
import cv2
import numpy as np
from typing import Dict, Any, Optional
from services.utils.hashing import sha256_obj


def compute_optical_flow(
    prev_frame: np.ndarray,
    curr_frame: np.ndarray
) -> np.ndarray:
    """Compute dense optical flow between frames.
    
    Args:
        prev_frame: Previous frame (BGR)
        curr_frame: Current frame (BGR)
        
    Returns:
        Optical flow field
    """
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray,
        None,
        pyr_scale=0.5,
        levels=3,
        winsize=15,
        iterations=3,
        poly_n=5,
        poly_sigma=1.2,
        flags=0
    )
    
    return flow


def analyze_camera_motion(flow: np.ndarray) -> Dict[str, Any]:
    """Analyze camera motion from optical flow.
    
    Args:
        flow: Optical flow field
        
    Returns:
        Camera motion analysis
    """
    # Compute average flow vectors
    avg_flow_x = float(np.mean(flow[:, :, 0]))
    avg_flow_y = float(np.mean(flow[:, :, 1]))
    
    magnitude = np.sqrt(avg_flow_x**2 + avg_flow_y**2)
    
    # Classify motion type
    motion_type = "static"
    if magnitude > 2.0:
        if abs(avg_flow_x) > abs(avg_flow_y) * 2:
            motion_type = "pan_horizontal"
        elif abs(avg_flow_y) > abs(avg_flow_x) * 2:
            motion_type = "pan_vertical"
        else:
            motion_type = "complex"
    
    return {
        "camera_motion": magnitude > 1.0,
        "motion_type": motion_type,
        "avg_flow": [round(avg_flow_x, 3), round(avg_flow_y, 3)],
        "magnitude": round(magnitude, 3)
    }


def compute_saliency(image: np.ndarray) -> np.ndarray:
    """Compute saliency map.
    
    Args:
        image: Input image
        
    Returns:
        Saliency map
    """
    # Use simple spectral residual method
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Compute FFT
    dft = cv2.dft(np.float32(gray), flags=cv2.DFT_COMPLEX_OUTPUT)
    magnitude = cv2.magnitude(dft[:, :, 0], dft[:, :, 1])
    
    # Log spectrum
    log_spectrum = np.log(magnitude + 1e-6)
    
    # Spectral residual
    blur = cv2.GaussianBlur(log_spectrum, (3, 3), 0)
    residual = log_spectrum - blur
    
    # Inverse FFT
    residual_complex = np.zeros_like(dft)
    residual_complex[:, :, 0] = residual
    
    saliency = cv2.idft(residual_complex)
    saliency = cv2.magnitude(saliency[:, :, 0], saliency[:, :, 1])
    
    # Normalize
    saliency = cv2.normalize(saliency, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    return saliency


def analyze_saliency(saliency: np.ndarray) -> Dict[str, Any]:
    """Analyze saliency map.
    
    Args:
        saliency: Saliency map
        
    Returns:
        Saliency analysis
    """
    # Find peak saliency regions
    threshold = np.percentile(saliency, 95)
    salient_mask = saliency > threshold
    
    # Compute center of mass
    y_coords, x_coords = np.where(salient_mask)
    if len(x_coords) > 0:
        center_x = float(np.mean(x_coords))
        center_y = float(np.mean(y_coords))
    else:
        center_x = saliency.shape[1] / 2
        center_y = saliency.shape[0] / 2
    
    # Normalize to [0, 1]
    center_x /= saliency.shape[1]
    center_y /= saliency.shape[0]
    
    return {
        "salient_center": [round(center_x, 3), round(center_y, 3)],
        "salient_area_pct": round(float(np.sum(salient_mask)) / salient_mask.size * 100, 2),
        "avg_saliency": round(float(np.mean(saliency)) / 255.0, 3)
    }


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze motion and saliency for a shot.
    
    Args:
        shot: Shot metadata with frame paths
        cfg: Configuration dictionary
        
    Returns:
        Motion and saliency analysis with provenance
    """
    params = {
        "flow_method": "farneback",
        "saliency_method": "spectral_residual"
    }
    
    # Load frames
    frame_paths = shot.get("frame_paths", [])
    if len(frame_paths) < 2:
        return {"motion": {}, "saliency": {}, "provenance": {}}
    
    # Load first and middle frames for flow
    frame1 = cv2.imread(frame_paths[0])
    mid_idx = len(frame_paths) // 2
    frame2 = cv2.imread(frame_paths[mid_idx])
    
    if frame1 is None or frame2 is None:
        return {"motion": {}, "saliency": {}, "provenance": {}}
    
    # Compute optical flow
    flow = compute_optical_flow(frame1, frame2)
    motion_analysis = analyze_camera_motion(flow)
    
    # Compute saliency on middle frame
    saliency_map = compute_saliency(frame2)
    saliency_analysis = analyze_saliency(saliency_map)
    
    provenance = {
        "tool": "opencv_flow_saliency",
        "version": "4.8.0",
        "params_hash": sha256_obj(params)
    }
    
    return {
        "motion": motion_analysis,
        "saliency": saliency_analysis,
        "provenance": provenance
    }
