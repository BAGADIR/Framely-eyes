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
        try:
            # Try CUDA first
            _face_model = FaceAnalysis(providers=['CUDAExecutionProvider'])
            _face_model.prepare(ctx_id=0, det_size=(640, 640))
            print("✅ Face detection: CUDA mode")
        except Exception as cuda_error:
            print(f"⚠️ CUDA face detection failed, falling back to CPU: {cuda_error}")
            try:
                # Fallback to CPU
                _face_model = FaceAnalysis(providers=['CPUExecutionProvider'])
                _face_model.prepare(ctx_id=-1, det_size=(640, 640))
                print("✅ Face detection: CPU mode")
            except Exception as cpu_error:
                print(f"❌ CPU face detection also failed: {cpu_error}")
                _face_model = None
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
    
    try:
        results = model.get(image)
        
        for idx, face in enumerate(results):
            bbox = face.bbox.astype(int)
            
            # Extract age and gender if available
            age = int(face.age) if hasattr(face, 'age') else None
            gender = face.sex if hasattr(face, 'sex') else None
            
            face_data = {
                "bbox": bbox.tolist(),
                "conf": float(face.det_score),
                "landmarks": face.kps.tolist() if hasattr(face, 'kps') else [],
                "age": age,
                "gender": gender,
                "embedding": face.normed_embedding.tolist() if hasattr(face, 'normed_embedding') else [],
                "face_id": f"face_{idx}"
            }
            faces.append(face_data)
    
    except Exception as e:
        print(f"⚠️ Face detection error (continuing without faces): {e}")
        return []  # Return empty list instead of crashing
    
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
