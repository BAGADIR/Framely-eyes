"""Production object tracking using ByteTrack.

Tracks objects across frames within a shot, maintaining persistent IDs.
Supports track lifecycle management: birth, persistence, re-identification, death.
"""
from typing import Dict, Any, List, Optional
import numpy as np

try:
    from yolox.tracker.byte_tracker import BYTETracker, STrack  # type: ignore
    BYTETRACK_AVAILABLE = True
except ImportError:
    BYTETRACK_AVAILABLE = False
    BYTETracker = None
    STrack = None

from services.utils.hashing import sha256_obj


# Global tracker state: {video_id: {shot_id: BYTETracker}}
_TRACKER_STATE: Dict[str, Dict[str, Any]] = {}


class SimpleTracker:
    """Fallback tracker when ByteTrack is unavailable."""
    
    def __init__(self):
        self.next_id = 0
        self.last_boxes = []
    
    def update(self, detections: np.ndarray) -> List[Dict[str, Any]]:
        """Assign IDs based on IoU matching with previous frame."""
        if len(detections) == 0:
            self.last_boxes = []
            return []
        
        tracks = []
        current_boxes = []
        
        for det in detections:
            x1, y1, x2, y2, conf = det
            box = [x1, y1, x2, y2]
            
            # Simple IoU matching with previous frame
            track_id = self._match_box(box)
            if track_id is None:
                track_id = self.next_id
                self.next_id += 1
            
            tracks.append({
                'track_id': track_id,
                'bbox': box,
                'confidence': float(conf)
            })
            current_boxes.append(box)
        
        self.last_boxes = current_boxes
        return tracks
    
    def _match_box(self, box: List[float]) -> Optional[int]:
        """Match box to previous frame using IoU."""
        if not self.last_boxes:
            return None
        
        best_iou = 0.0
        best_idx = -1
        
        for idx, prev_box in enumerate(self.last_boxes):
            iou = self._compute_iou(box, prev_box)
            if iou > best_iou:
                best_iou = iou
                best_idx = idx
        
        if best_iou > 0.5:  # IoU threshold
            return best_idx
        return None
    
    @staticmethod
    def _compute_iou(box1: List[float], box2: List[float]) -> float:
        """Compute intersection over union."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        
        return inter / union if union > 0 else 0.0


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Assign persistent track IDs to detected objects across frames.

    Args:
        shot: Shot metadata with:
            - video_id: Video identifier
            - shot_id: Shot identifier
            - detectors.objects: List of detected objects with bbox, confidence, label
            - fps: Frames per second (for track buffer calculation)
            - start_frame: Starting frame number

        cfg: Configuration dictionary with:
            - detect.track.engine: 'bytetrack' or 'simple'
            - detect.track.window: Track buffer frames (default: 5)
            - detect.track.min_hits: Minimum detections to confirm track (default: 2)

    Returns:
        Dict with:
            - objects: List of objects with added 'track_id' field
            - provenance: Tracking metadata
    """
    video_id = shot.get("video_id", "unknown")
    shot_id = shot.get("shot_id", "unknown")
    objects: List[Dict[str, Any]] = shot.get("detectors", {}).get("objects", []) or []
    fps = shot.get("fps", 30)

    if not objects:
        return {"objects": [], "provenance": _build_provenance("no_objects", cfg)}

    # Get or create tracker for this shot
    tracker = _get_tracker(video_id, shot_id, fps, cfg)

    # Convert objects to detection format: [x1, y1, x2, y2, conf]
    detections = _objects_to_detections(objects)

    # Update tracker
    if BYTETRACK_AVAILABLE and isinstance(tracker, BYTETracker):
        # ByteTrack expects numpy array
        det_array = np.array(detections, dtype=np.float32)
        
        # Get frame resolution from first object (assuming all same)
        frame_h = shot.get("frame_height", 1080)
        frame_w = shot.get("frame_width", 1920)
        
        # Update tracker and get online tracks
        online_targets = tracker.update(
            det_array,
            img_info=[frame_h, frame_w],
            img_size=[frame_h, frame_w]
        )
        
        # Assign track IDs from ByteTrack
        for i, track in enumerate(online_targets):
            if i < len(objects):
                objects[i]["track_id"] = int(track.track_id)
                # Add tracking quality metadata
                objects[i]["track_score"] = float(track.score)
                objects[i]["track_age"] = int(track.frame_id - track.start_frame)
    else:
        # Fallback to simple tracker
        det_array = np.array(detections, dtype=np.float32)
        tracked = tracker.update(det_array)
        
        for i, track_info in enumerate(tracked):
            if i < len(objects):
                objects[i]["track_id"] = track_info["track_id"]

    return {
        "objects": objects,
        "provenance": _build_provenance(
            "bytetrack" if BYTETRACK_AVAILABLE else "simple",
            cfg
        )
    }


def _get_tracker(video_id: str, shot_id: str, fps: float, cfg: Dict[str, Any]) -> Any:
    """Get or create tracker instance for this shot."""
    global _TRACKER_STATE
    
    if video_id not in _TRACKER_STATE:
        _TRACKER_STATE[video_id] = {}
    
    if shot_id not in _TRACKER_STATE[video_id]:
        track_cfg = cfg.get("detect", {}).get("track", {})
        
        if BYTETRACK_AVAILABLE:
            # Create ByteTrack instance
            _TRACKER_STATE[video_id][shot_id] = BYTETracker(
                track_thresh=0.5,      # High confidence threshold
                track_buffer=track_cfg.get("window", 5),  # From config
                match_thresh=0.8,      # IoU threshold for matching
                frame_rate=fps
            )
        else:
            # Fallback to simple tracker
            _TRACKER_STATE[video_id][shot_id] = SimpleTracker()
    
    return _TRACKER_STATE[video_id][shot_id]


def _objects_to_detections(objects: List[Dict[str, Any]]) -> List[List[float]]:
    """Convert object dicts to detection arrays [x1, y1, x2, y2, conf]."""
    detections = []
    
    for obj in objects:
        bbox = obj.get("bbox", [])
        if len(bbox) != 4:
            continue
        
        # bbox format: [x, y, width, height] → convert to [x1, y1, x2, y2]
        x, y, w, h = bbox
        x1, y1 = x, y
        x2, y2 = x + w, y + h
        
        conf = obj.get("confidence", 1.0)
        
        detections.append([x1, y1, x2, y2, conf])
    
    return detections


def _build_provenance(engine: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Build provenance metadata for tracking."""
    track_cfg = cfg.get("detect", {}).get("track", {})
    
    params = {
        "engine": engine,
        "window": track_cfg.get("window", 5),
        "min_hits": track_cfg.get("min_hits", 2),
        "available": BYTETRACK_AVAILABLE
    }
    
    return {
        "tool": "tracker",
        "version": "1.0.0",
        "ckpt": None,
        "params_hash": sha256_obj(params),
    }


def reset_tracker(video_id: Optional[str] = None, shot_id: Optional[str] = None) -> None:
    """Reset tracker state. Call this when starting a new video or shot.
    
    Args:
        video_id: If specified, reset only this video's trackers
        shot_id: If specified with video_id, reset only this specific shot
    """
    global _TRACKER_STATE
    
    if video_id is None:
        _TRACKER_STATE.clear()
    elif shot_id is None:
        if video_id in _TRACKER_STATE:
            del _TRACKER_STATE[video_id]
    else:
        if video_id in _TRACKER_STATE and shot_id in _TRACKER_STATE[video_id]:
            del _TRACKER_STATE[video_id][shot_id]
