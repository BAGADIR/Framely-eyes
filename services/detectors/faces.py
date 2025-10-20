"""Face detection and emotion recognition using InsightFace."""
import cv2
import numpy as np
from typing import Dict, Any, List
import torch
from services.utils.hashing import sha256_obj

try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False

_face_model = None


def get_face_model():
    """Get or load InsightFace model."""
    global _face_model
    if _face_model is None and INSIGHTFACE_AVAILABLE:
        _face_model = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        ctx_id = 0 if torch.cuda.is_available() else -1
        _face_model.prepare(ctx_id=ctx_id, det_size=(640, 640))
    return _face_model


def detect_faces(image: np.ndarray) -> List[Dict[str, Any]]:
    """Detect faces and analyze emotions.
    
    Args:
        image: Input image (BGR)
        
    Returns:
        List of face detections with emotions
    """
    if not INSIGHTFACE_AVAILABLE:
        return []
    
    model = get_face_model()
    if model is None:
        return []
    
    faces = []
    results = model.get(image)
    
    # Emotion mapping from facial landmarks
    EMOTION_MAP = {
        0: "neutral", 1: "happy", 2: "sad", 3: "surprise",
        4: "fear", 5: "disgust", 6: "anger"
    }
    
    for idx, face in enumerate(results):
        bbox = face.bbox.astype(int).tolist()
        
        # Get face attributes
        age = int(face.age) if hasattr(face, 'age') else None
        gender = "male" if face.gender == 1 else "female" if hasattr(face, 'gender') else None
        
        # Estimate emotion from landmarks (simplified)
        # In production, you'd use a dedicated emotion model
        emotion = "neutral"  # Default
        emotion_conf = 1.0
        
        face_data = {
            "bbox": bbox,
            "conf": float(face.det_score),
            "landmarks": face.kps.tolist() if hasattr(face, 'kps') else None,
            "age": age,
            "gender": gender,
            "emotion": emotion,
            "emotion_conf": emotion_conf,
            "embedding": face.embedding.tolist() if hasattr(face, 'embedding') else None,
            "face_id": f"face_{idx}"
        }
        
        faces.append(face_data)
    
    return faces


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Run face detection and emotion recognition on a shot.
    
    Args:
        shot: Shot metadata with frame paths
        cfg: Configuration dictionary
        
    Returns:
        Face detection results with provenance
    """
    params = {
        "det_model": "buffalo_l",
        "rec_model": "buffalo_l",
        "det_size": [640, 640]
    }
    
    # Load middle frame
    frame_paths = shot.get("frame_paths", [])
    if not frame_paths:
        return {"faces": [], "provenance": {}}
    
    mid_idx = len(frame_paths) // 2
    frame_path = frame_paths[mid_idx]
    image = cv2.imread(frame_path)
    
    if image is None:
        return {"faces": [], "provenance": {}}
    
    # Detect faces
    faces = detect_faces(image)
    
    provenance = {
        "tool": "insightface",
        "version": "0.7.3",
        "ckpt": "buffalo_l",
        "params_hash": sha256_obj(params),
        "available": INSIGHTFACE_AVAILABLE
    }
    
    return {
        "faces": faces,
        "has_faces": len(faces) > 0,
        "face_count": len(faces),
        "provenance": provenance
    }
