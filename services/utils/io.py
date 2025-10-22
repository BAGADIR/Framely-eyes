"""I/O utilities for video processing and storage."""
import os
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
import cv2
import numpy as np


class NumpyJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types (ints, floats, bools, arrays)."""
    def default(self, obj: Any):  # type: ignore[override]
        # Scalars
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        # Arrays
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def ensure_dir(path: str) -> str:
    """Ensure directory exists, create if needed.
    
    Args:
        path: Directory path
        
    Returns:
        Absolute path to directory
    """
    Path(path).mkdir(parents=True, exist_ok=True)
    return str(Path(path).absolute())


def get_video_dir(video_id: str, base_path: str = "store") -> str:
    """Get video-specific directory path.
    
    Args:
        video_id: Unique video identifier
        base_path: Base storage path
        
    Returns:
        Path to video directory
    """
    video_dir = os.path.join(base_path, video_id)
    return ensure_dir(video_dir)


def get_frames_dir(video_id: str, base_path: str = "store") -> str:
    """Get frames directory path.
    
    Args:
        video_id: Unique video identifier
        base_path: Base storage path
        
    Returns:
        Path to frames directory
    """
    frames_dir = os.path.join(base_path, video_id, "frames")
    return ensure_dir(frames_dir)


def save_frame(frame: np.ndarray, video_id: str, frame_num: int, base_path: str = "store") -> str:
    """Save a video frame as image.
    
    Args:
        frame: Frame as numpy array (BGR)
        video_id: Unique video identifier
        frame_num: Frame number
        base_path: Base storage path
        
    Returns:
        Path to saved frame
    """
    frames_dir = get_frames_dir(video_id, base_path)
    frame_path = os.path.join(frames_dir, f"frame_{frame_num:08d}.jpg")
    cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return frame_path


def load_frame(video_id: str, frame_num: int, base_path: str = "store") -> Optional[np.ndarray]:
    """Load a video frame from disk.
    
    Args:
        video_id: Unique video identifier
        frame_num: Frame number
        base_path: Base storage path
        
    Returns:
        Frame as numpy array (BGR) or None if not found
    """
    frames_dir = get_frames_dir(video_id, base_path)
    frame_path = os.path.join(frames_dir, f"frame_{frame_num:08d}.jpg")
    if os.path.exists(frame_path):
        return cv2.imread(frame_path)
    return None


def save_json(data: Dict[str, Any], path: str) -> None:
    """Save dictionary as JSON file.
    
    Args:
        data: Data to save
        path: Output file path
    """
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        # Use numpy-safe encoder to avoid TypeError for numpy scalar types
        json.dump(data, f, indent=2, ensure_ascii=False, cls=NumpyJSONEncoder)


def load_json(path: str) -> Dict[str, Any]:
    """Load JSON file as dictionary.
    
    Args:
        path: Input file path
        
    Returns:
        Loaded data
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_vab(video_id: str, vab: Dict[str, Any], base_path: str = "store") -> str:
    """Save VAB (Video Analysis Bundle) to disk.
    
    Args:
        video_id: Unique video identifier
        vab: VAB dictionary
        base_path: Base storage path
        
    Returns:
        Path to saved VAB file
    """
    video_dir = get_video_dir(video_id, base_path)
    vab_path = os.path.join(video_dir, "vab.json")
    save_json(vab, vab_path)
    return vab_path


def load_vab(video_id: str, base_path: str = "store") -> Optional[Dict[str, Any]]:
    """Load VAB from disk.
    
    Args:
        video_id: Unique video identifier
        base_path: Base storage path
        
    Returns:
        VAB dictionary or None if not found
    """
    video_dir = get_video_dir(video_id, base_path)
    vab_path = os.path.join(video_dir, "vab.json")
    if os.path.exists(vab_path):
        return load_json(vab_path)
    return None


def cleanup_video_dir(video_id: str, base_path: str = "store", keep_vab: bool = True) -> None:
    """Clean up video directory, optionally keeping VAB.
    
    Args:
        video_id: Unique video identifier
        base_path: Base storage path
        keep_vab: Whether to keep the VAB file
    """
    video_dir = get_video_dir(video_id, base_path)
    
    if keep_vab:
        # Remove frames directory
        frames_dir = os.path.join(video_dir, "frames")
        if os.path.exists(frames_dir):
            shutil.rmtree(frames_dir)
        
        # Remove video file
        for ext in ['.mp4', '.mov', '.mkv', '.avi']:
            video_path = os.path.join(video_dir, f"video{ext}")
            if os.path.exists(video_path):
                os.remove(video_path)
    else:
        # Remove entire directory
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)
