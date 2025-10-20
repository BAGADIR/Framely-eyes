"""Real-ESRGAN super-resolution for enhancing small objects."""
import cv2
import numpy as np
from typing import Dict, Any, Optional
from services.utils.hashing import sha256_obj

# Note: Real-ESRGAN integration skeleton
# In production, use: from realesrgan import RealESRGANer


_sr_model = None


def get_sr_model():
    """Get or load Real-ESRGAN model."""
    global _sr_model
    if _sr_model is None:
        # TODO: Initialize Real-ESRGAN model
        # from realesrgan import RealESRGANer
        # _sr_model = RealESRGANer(...)
        pass
    return _sr_model


def upscale_image(image: np.ndarray, scale: int = 4) -> np.ndarray:
    """Upscale image using Real-ESRGAN.
    
    Args:
        image: Input image
        scale: Upscaling factor
        
    Returns:
        Upscaled image
    """
    # Placeholder: use simple interpolation
    # In production, use Real-ESRGAN model
    h, w = image.shape[:2]
    return cv2.resize(image, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)


def should_upscale(image: np.ndarray, trigger_min_h: int = 1440) -> bool:
    """Determine if image should be upscaled.
    
    Args:
        image: Input image
        trigger_min_h: Minimum height to trigger upscaling
        
    Returns:
        True if upscaling recommended
    """
    h, w = image.shape[:2]
    return h < trigger_min_h


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Apply super-resolution enhancement if needed.
    
    Args:
        shot: Shot metadata with frame paths
        cfg: Configuration dictionary
        
    Returns:
        Super-resolution results with provenance
    """
    sr_cfg = cfg.get("detect", {}).get("superres", {})
    
    if not sr_cfg.get("enabled", True):
        return {"sr_used": False, "provenance": {}}
    
    params = {
        "engine": sr_cfg.get("engine", "realesrgan_x4plus"),
        "scale": 4,
        "trigger_min_h": sr_cfg.get("trigger_min_h", 1440)
    }
    
    # Load middle frame
    frame_paths = shot.get("frame_paths", [])
    if not frame_paths:
        return {"sr_used": False, "provenance": {}}
    
    mid_idx = len(frame_paths) // 2
    frame_path = frame_paths[mid_idx]
    image = cv2.imread(frame_path)
    
    if image is None:
        return {"sr_used": False, "provenance": {}}
    
    # Check if upscaling is needed
    if not should_upscale(image, params["trigger_min_h"]):
        return {"sr_used": False, "provenance": {}}
    
    # Apply super-resolution
    upscaled = upscale_image(image, params["scale"])
    
    # Save upscaled frame (overwrite or save separately)
    # cv2.imwrite(frame_path.replace(".jpg", "_sr.jpg"), upscaled)
    
    provenance = {
        "tool": "realesrgan",
        "version": "0.3.0",
        "ckpt": "RealESRGAN_x4plus.pth",
        "params_hash": sha256_obj(params)
    }
    
    return {
        "sr_used": True,
        "original_size": image.shape[:2],
        "upscaled_size": upscaled.shape[:2],
        "provenance": provenance
    }
