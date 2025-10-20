"""YOLO-based object detection."""
import cv2
import numpy as np
from typing import Dict, Any, List
from ultralytics import YOLO
from services.utils.hashing import sha256_obj


# Global model cache
_yolo_model = None


def get_yolo_model(checkpoint: str = "yolov8m.pt") -> YOLO:
    """Get or load YOLO model.
    
    Args:
        checkpoint: Model checkpoint name
        
    Returns:
        YOLO model instance
    """
    global _yolo_model
    if _yolo_model is None:
        _yolo_model = YOLO(checkpoint)
    return _yolo_model


def detect_objects(
    image: np.ndarray,
    conf_threshold: float = 0.18,
    iou_threshold: float = 0.65
) -> List[Dict[str, Any]]:
    """Detect objects in image using YOLO.
    
    Args:
        image: Input image (BGR)
        conf_threshold: Confidence threshold
        iou_threshold: IoU threshold for NMS
        
    Returns:
        List of detected objects
    """
    model = get_yolo_model()
    
    results = model.predict(
        image,
        conf=conf_threshold,
        iou=iou_threshold,
        verbose=False
    )
    
    detections = []
    for result in results:
        boxes = result.boxes
        for i in range(len(boxes)):
            box = boxes[i]
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = model.names[cls]
            
            detection = {
                "label": label,
                "conf": round(conf, 3),
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "area": float((x2 - x1) * (y2 - y1)),
                "class_id": cls
            }
            detections.append(detection)
    
    return detections


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Run YOLO detection on a shot.
    
    Args:
        shot: Shot metadata with frame paths
        cfg: Configuration dictionary
        
    Returns:
        Detection results with provenance
    """
    params = {
        "model": "yolov8m",
        "input": 640,
        "conf": 0.18,
        "iou": 0.65
    }
    
    # Load middle frame of shot
    frame_paths = shot.get("frame_paths", [])
    if not frame_paths:
        return {"objects": [], "provenance": {}}
    
    mid_idx = len(frame_paths) // 2
    frame_path = frame_paths[mid_idx]
    image = cv2.imread(frame_path)
    
    if image is None:
        return {"objects": [], "provenance": {}}
    
    # Run detection
    objects = detect_objects(image, params["conf"], params["iou"])
    
    # Add provenance
    provenance = {
        "tool": "yolo",
        "version": "8.3.2",
        "ckpt": "yolov8m.pt",
        "params_hash": sha256_obj(params)
    }
    
    return {
        "objects": objects,
        "provenance": provenance
    }
