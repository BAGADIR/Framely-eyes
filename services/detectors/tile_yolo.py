"""Tiled YOLO detection for small objects with two-pass refinement."""
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
from services.detectors.yolo import get_yolo_model
from services.utils.hashing import sha256_obj


def tile_image(
    image: np.ndarray,
    tile_size: int = 512,
    stride: int = 256
) -> List[Tuple[np.ndarray, int, int]]:
    """Split image into overlapping tiles.
    
    Args:
        image: Input image
        tile_size: Size of each tile
        stride: Stride between tiles
        
    Returns:
        List of (tile, x_offset, y_offset)
    """
    h, w = image.shape[:2]
    tiles = []
    
    for y in range(0, h - tile_size + 1, stride):
        for x in range(0, w - tile_size + 1, stride):
            tile = image[y:y+tile_size, x:x+tile_size]
            tiles.append((tile, x, y))
    
    # Handle edges
    if w % stride != 0:
        for y in range(0, h - tile_size + 1, stride):
            tile = image[y:y+tile_size, w-tile_size:w]
            tiles.append((tile, w-tile_size, y))
    
    if h % stride != 0:
        for x in range(0, w - tile_size + 1, stride):
            tile = image[h-tile_size:h, x:x+tile_size]
            tiles.append((tile, x, h-tile_size))
    
    # Bottom-right corner
    if h % stride != 0 and w % stride != 0:
        tile = image[h-tile_size:h, w-tile_size:w]
        tiles.append((tile, w-tile_size, h-tile_size))
    
    return tiles


def detect_tiled(
    image: np.ndarray,
    tile_size: int = 512,
    stride: int = 256,
    conf_threshold: float = 0.18
) -> List[Dict[str, Any]]:
    """Run YOLO on tiled image for better small object detection.
    
    Args:
        image: Input image
        tile_size: Size of each tile
        stride: Stride between tiles
        conf_threshold: Confidence threshold
        
    Returns:
        List of detections in global coordinates
    """
    model = get_yolo_model()
    tiles = tile_image(image, tile_size, stride)
    
    all_detections = []
    
    for tile, x_offset, y_offset in tiles:
        results = model.predict(tile, conf=conf_threshold, verbose=False)
        
        for result in results:
            boxes = result.boxes
            for i in range(len(boxes)):
                box = boxes[i]
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # Convert to global coordinates
                x1 += x_offset
                y1 += y_offset
                x2 += x_offset
                y2 += y_offset
                
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
                all_detections.append(detection)
    
    # Simple NMS to remove duplicates from overlapping tiles
    return nms_detections(all_detections, iou_threshold=0.5)


def nms_detections(
    detections: List[Dict[str, Any]],
    iou_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """Apply Non-Maximum Suppression to remove duplicate detections.
    
    Args:
        detections: List of detections
        iou_threshold: IoU threshold for suppression
        
    Returns:
        Filtered list of detections
    """
    if not detections:
        return []
    
    # Convert to numpy arrays
    boxes = np.array([d["bbox"] for d in detections])
    scores = np.array([d["conf"] for d in detections])
    
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    
    return [detections[i] for i in keep]


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Run tiled YOLO detection on a shot.
    
    Args:
        shot: Shot metadata with frame paths
        cfg: Configuration dictionary
        
    Returns:
        Detection results with provenance
    """
    tile_cfg = cfg.get("detect", {}).get("tile", {})
    params = {
        "model": "yolov8m",
        "tile_size": tile_cfg.get("size", 512),
        "stride": tile_cfg.get("stride", 256),
        "conf": 0.18
    }
    
    # Load middle frame
    frame_paths = shot.get("frame_paths", [])
    if not frame_paths:
        return {"objects": [], "provenance": {}}
    
    mid_idx = len(frame_paths) // 2
    frame_path = frame_paths[mid_idx]
    image = cv2.imread(frame_path)
    
    if image is None:
        return {"objects": [], "provenance": {}}
    
    # Run tiled detection
    objects = detect_tiled(
        image,
        params["tile_size"],
        params["stride"],
        params["conf"]
    )
    
    provenance = {
        "tool": "tile_yolo",
        "version": "8.3.2",
        "ckpt": "yolov8m.pt",
        "params_hash": sha256_obj(params)
    }
    
    return {
        "objects": objects,
        "provenance": provenance
    }
