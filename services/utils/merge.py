"""Utilities for merging shot bundles into scenes and final VAB."""
from typing import List, Dict, Any
import numpy as np


def merge_detections(shot_bundles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge object detections across shots.
    
    Args:
        shot_bundles: List of shot analysis bundles
        
    Returns:
        Merged detection statistics
    """
    all_objects = []
    all_faces = []
    all_text = []
    
    for shot in shot_bundles:
        detectors = shot.get("detectors", {})
        
        # Collect objects
        if "objects" in detectors:
            all_objects.extend(detectors["objects"])
        
        # Collect faces
        if "faces" in detectors:
            all_faces.extend(detectors["faces"])
        
        # Collect text
        if "text" in detectors:
            all_text.extend(detectors["text"])
    
    # Count unique labels
    object_counts = {}
    for obj in all_objects:
        label = obj.get("label", "unknown")
        object_counts[label] = object_counts.get(label, 0) + 1
    
    return {
        "total_objects": len(all_objects),
        "total_faces": len(all_faces),
        "total_text_regions": len(all_text),
        "object_counts": object_counts,
        "unique_object_classes": len(object_counts)
    }


def compute_scene_features(shot_bundles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate features for a scene from its shots.
    
    Args:
        shot_bundles: List of shot analysis bundles in scene
        
    Returns:
        Scene-level features
    """
    if not shot_bundles:
        return {}
    
    # Compute average brightness
    brightness_values = [
        s.get("detectors", {}).get("color", {}).get("brightness", 0.5)
        for s in shot_bundles
    ]
    avg_brightness = np.mean(brightness_values) if brightness_values else 0.5
    
    # Compute dominant mood
    moods = [s.get("mood", "neutral") for s in shot_bundles]
    mood_counts = {}
    for mood in moods:
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
    dominant_mood = max(mood_counts.items(), key=lambda x: x[1])[0] if mood_counts else "neutral"
    
    # Check for motion
    has_camera_motion = any(
        s.get("detectors", {}).get("motion", {}).get("camera_motion", False)
        for s in shot_bundles
    )
    
    # Aggregate audio features
    audio_features = {
        "avg_loudness": np.mean([
            s.get("detectors", {}).get("audio", {}).get("lufs", -14.0)
            for s in shot_bundles
        ]),
        "has_speech": any(
            s.get("detectors", {}).get("audio", {}).get("has_speech", False)
            for s in shot_bundles
        ),
        "has_music": any(
            s.get("detectors", {}).get("audio", {}).get("has_music", False)
            for s in shot_bundles
        )
    }
    
    return {
        "avg_brightness": round(avg_brightness, 3),
        "dominant_mood": dominant_mood,
        "has_camera_motion": has_camera_motion,
        "shot_count": len(shot_bundles),
        "total_duration_s": sum(s.get("duration_s", 0) for s in shot_bundles),
        "audio": audio_features
    }


def build_scenes(
    shot_bundles: List[Dict[str, Any]],
    meta: Dict[str, Any],
    cfg: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Group shots into scenes based on temporal continuity and similarity.
    
    Args:
        shot_bundles: List of all shot analysis bundles
        meta: Video metadata
        cfg: Configuration dict
        
    Returns:
        List of scene dictionaries
    """
    if not shot_bundles:
        return []
    
    scenes = []
    current_scene_shots = [shot_bundles[0]]
    scene_id = 0
    
    for i in range(1, len(shot_bundles)):
        prev_shot = shot_bundles[i - 1]
        curr_shot = shot_bundles[i]
        
        # Simple heuristic: group shots if they have similar visual features
        # In production, use more sophisticated scene boundary detection
        prev_brightness = prev_shot.get("detectors", {}).get("color", {}).get("brightness", 0.5)
        curr_brightness = curr_shot.get("detectors", {}).get("color", {}).get("brightness", 0.5)
        
        # If brightness change is significant, start new scene
        if abs(prev_brightness - curr_brightness) > 0.3:
            # Save current scene
            scene = {
                "scene_id": f"sc_{scene_id:03d}",
                "shots": [s["shot_id"] for s in current_scene_shots],
                "start_frame": current_scene_shots[0].get("start_frame", 0),
                "end_frame": current_scene_shots[-1].get("end_frame", 0),
                "features": compute_scene_features(current_scene_shots)
            }
            scenes.append(scene)
            
            # Start new scene
            current_scene_shots = [curr_shot]
            scene_id += 1
        else:
            current_scene_shots.append(curr_shot)
    
    # Add final scene
    if current_scene_shots:
        scene = {
            "scene_id": f"sc_{scene_id:03d}",
            "shots": [s["shot_id"] for s in current_scene_shots],
            "start_frame": current_scene_shots[0].get("start_frame", 0),
            "end_frame": current_scene_shots[-1].get("end_frame", 0),
            "features": compute_scene_features(current_scene_shots)
        }
        scenes.append(scene)
    
    return scenes


def assemble_vab(
    meta: Dict[str, Any],
    scenes: List[Dict[str, Any]],
    shot_bundles: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Assemble final VAB (Video Analysis Bundle).
    
    Args:
        meta: Video metadata
        scenes: List of scene dictionaries
        shot_bundles: List of shot analysis bundles
        
    Returns:
        Complete VAB dictionary
    """
    # Build tracks (persistent objects across shots)
    tracks = []  # TODO: Implement tracking across shots
    
    # Global statistics
    global_stats = {
        "total_frames": meta.get("frames", 0),
        "duration_s": meta.get("duration", 0.0),
        "fps": meta.get("fps", 30.0),
        "resolution": {
            "width": meta.get("width", 0),
            "height": meta.get("height", 0)
        },
        "detections": merge_detections(shot_bundles)
    }
    
    vab = {
        "schema_version": "1.1.0",
        "video": {
            "video_id": meta.get("video_id"),
            "path": meta.get("path"),
            "sha256": meta.get("sha256")
        },
        "global": global_stats,
        "scenes": scenes,
        "shots": shot_bundles,
        "tracks": tracks
    }
    
    return vab
