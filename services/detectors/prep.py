"""Video preparation: decode, extract keyframes, slice audio."""
import os
import cv2
import subprocess
from typing import Dict, Any, List, Optional
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from services.utils.io import get_video_dir, ensure_dir, get_frames_dir
from services.utils.hashing import sha256_file
import numpy as np


def download_video(url: str, video_id: str, base_path: str = "store") -> str:
    """Download video from URL.
    
    Args:
        url: Video URL
        video_id: Unique video identifier
        base_path: Base storage path
        
    Returns:
        Path to downloaded video
    """
    video_dir = get_video_dir(video_id, base_path)
    output_path = os.path.join(video_dir, "video.mp4")
    
    # Use ffmpeg to download and normalize
    cmd = [
        "ffmpeg", "-y",
        "-i", url,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def get_video_metadata(video_path: str) -> Dict[str, Any]:
    """Extract video metadata using OpenCV.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Metadata dictionary
    """
    cap = cv2.VideoCapture(video_path)
    
    metadata = {
        "path": video_path,
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "duration": 0.0,
        "sha256": sha256_file(video_path)
    }
    
    if metadata["fps"] > 0:
        metadata["duration"] = metadata["frames"] / metadata["fps"]
    
    cap.release()
    return metadata


def detect_shots(video_path: str, threshold: float = 27.0) -> List[tuple]:
    """Detect shot boundaries using PySceneDetect.
    
    Args:
        video_path: Path to video file
        threshold: Content detection threshold
        
    Returns:
        List of (start_frame, end_frame) tuples
    """
    try:
        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))
        try:
            video_manager.start()
            scene_manager.detect_scenes(video_manager)
            scene_list = scene_manager.get_scene_list()
        finally:
            video_manager.release()
    except Exception:
        scene_list = []
    
    shots = []
    for i, scene in enumerate(scene_list):
        start_frame = scene[0].get_frames()
        end_frame = scene[1].get_frames()
        shots.append((start_frame, end_frame))
    
    if not shots:
        cap = cv2.VideoCapture(video_path)
        prev_gray = None
        start_idx = 0
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                score = float(np.mean(diff))
                if score > 25.0:
                    shots.append((start_idx, max(idx - 1, start_idx)))
                    start_idx = idx
            prev_gray = gray
            idx += 1
        total = idx
        cap.release()
        if total > 0:
            shots.append((start_idx, total - 1))
    
    return shots


def extract_keyframes(
    video_path: str,
    video_id: str,
    frame_stride: int = 1,
    base_path: str = "store"
) -> List[Dict[str, Any]]:
    """Extract keyframes from video.
    
    Args:
        video_path: Path to video file
        video_id: Unique video identifier
        frame_stride: Extract every Nth frame (1 = all frames)
        base_path: Base storage path
        
    Returns:
        List of keyframe metadata
    """
    frames_dir = get_frames_dir(video_id, base_path)
    cap = cv2.VideoCapture(video_path)
    
    keyframes = []
    frame_num = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_num % frame_stride == 0:
            frame_path = os.path.join(frames_dir, f"frame_{frame_num:08d}.jpg")
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            keyframes.append({
                "frame_num": frame_num,
                "path": frame_path,
                "timestamp": frame_num / cap.get(cv2.CAP_PROP_FPS)
            })
        
        frame_num += 1
    
    cap.release()
    return keyframes


def extract_audio(video_path: str, video_id: str, base_path: str = "store") -> str:
    """Extract audio track from video.
    
    Args:
        video_path: Path to video file
        video_id: Unique video identifier
        base_path: Base storage path
        
    Returns:
        Path to extracted audio file
    """
    video_dir = get_video_dir(video_id, base_path)
    audio_path = os.path.join(video_dir, "audio.wav")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "2",
        audio_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return audio_path
    except subprocess.CalledProcessError as e:
        print(f"Warning: Audio extraction failed (video may have no audio track): {e}")
        return None


def prepare(
    video_id: str,
    media_url: Optional[str] = None,
    cfg: Optional[Dict[str, Any]] = None,
    base_path: str = "store"
) -> Dict[str, Any]:
    """Prepare video for analysis: download, decode, detect shots, extract frames and audio.
    
    Args:
        video_id: Unique video identifier
        media_url: URL to video file (if remote)
        cfg: Configuration dictionary
        base_path: Base storage path
        
    Returns:
        Preparation metadata including shots and keyframes
    """
    if cfg is None:
        cfg = {"runtime": {"frame_stride": 1}}
    
    # Download or locate video
    if media_url:
        video_path = download_video(media_url, video_id, base_path)
    else:
        # Assume video already in store
        video_dir = get_video_dir(video_id, base_path)
        video_path = os.path.join(video_dir, "video.mp4")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Extract metadata
    metadata = get_video_metadata(video_path)
    metadata["video_id"] = video_id
    
    # Detect shot boundaries
    shot_boundaries = detect_shots(video_path)
    
    # Build shot metadata
    shots = []
    for i, (start_frame, end_frame) in enumerate(shot_boundaries):
        shot = {
            "shot_id": f"sh_{i:03d}",
            "start_frame": start_frame,
            "end_frame": end_frame,
            "frame_count": end_frame - start_frame,
            "duration_s": (end_frame - start_frame) / metadata["fps"]
        }
        shots.append(shot)
    
    metadata["shots"] = shots
    
    # Extract keyframes
    frame_stride = cfg.get("runtime", {}).get("frame_stride", 1)
    keyframes = extract_keyframes(video_path, video_id, frame_stride, base_path)
    metadata["keyframes"] = keyframes
    
    # Extract audio
    audio_path = extract_audio(video_path, video_id, base_path)
    metadata["audio_path"] = audio_path
    
    return metadata
