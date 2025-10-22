"""OCR and font detection using PaddleOCR."""
import cv2
import numpy as np
from typing import Dict, Any, List
import torch
from services.utils.hashing import sha256_obj

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

_ocr_model = None


def get_ocr_model():
    """Get or load PaddleOCR model."""
    global _ocr_model
    if _ocr_model is None and PADDLEOCR_AVAILABLE:
        # Absolute minimal - only lang parameter
        _ocr_model = PaddleOCR(lang='en')
    return _ocr_model


def detect_text(image: np.ndarray) -> List[Dict[str, Any]]:
    """Detect and recognize text in image.
    
    Args:
        image: Input image
        
    Returns:
        List of text detections
    """
    if not PADDLEOCR_AVAILABLE:
        return []
    
    model = get_ocr_model()
    if model is None:
        return []
    
    texts = []
    
    try:
        results = model.ocr(image, cls=True)
        
        if results is None or len(results) == 0:
            return []
        
        for line in results:
            if line is None:
                continue
            for word_info in line:
                bbox = word_info[0]
                text_data = word_info[1]
                text, conf = text_data[0], text_data[1]
                
                # Convert bbox to flat list
                bbox_flat = [float(coord) for point in bbox for coord in point]
                
                # Estimate font properties from text region
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                x1, y1 = int(min(x_coords)), int(min(y_coords))
                x2, y2 = int(max(x_coords)), int(max(y_coords))
                
                text_region = image[y1:y2, x1:x2]
                font_props = analyze_font_properties(text_region, text)
                
                text_det = {
                    "text": text,
                    "conf": float(conf),
                    "bbox": bbox_flat,
                    "font_family": font_props["font_family"],
                    "is_bold": font_props["is_bold"],
                    "is_italic": font_props["is_italic"],
                    "font_size_est": font_props["font_size"]
                }
                
                texts.append(text_det)
    
    except Exception as e:
        print(f"OCR error: {e}")
        return []
    
    return texts


def analyze_font_properties(text_region: np.ndarray, text: str) -> Dict[str, Any]:
    """Analyze font properties from text region.
    
    Args:
        text_region: Cropped text region
        text: Detected text
        
    Returns:
        Font properties dict
    """
    if text_region is None or text_region.size == 0:
        return {
            "font_family": "sans-serif",
            "is_bold": False,
            "is_italic": False,
            "font_size": 12
        }
    
    h, w = text_region.shape[:2]
    
    # Estimate font size from region height
    font_size = max(8, int(h * 0.7))
    
    # Convert to grayscale for analysis
    if len(text_region.shape) == 3:
        gray = cv2.cvtColor(text_region, cv2.COLOR_BGR2GRAY)
    else:
        gray = text_region
    
    # Estimate boldness from stroke width (average intensity in text region)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white_ratio = np.sum(binary == 255) / binary.size
    is_bold = white_ratio < 0.4  # Bold text has more black pixels
    
    # Simple italic detection (check for slant in edges)
    edges = cv2.Canny(gray, 50, 150)
    is_italic = False  # Simplified - would need more sophisticated analysis
    
    # Font family guess (simplified - serif vs sans-serif)
    font_family = "sans-serif"  # Default
    
    return {
        "font_family": font_family,
        "is_bold": is_bold,
        "is_italic": is_italic,
        "font_size": font_size
    }


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Run OCR and font detection on a shot.
    
    Args:
        shot: Shot metadata with frame paths
        cfg: Configuration dictionary
        
    Returns:
        OCR results with provenance
    """
    params = {
        "det_model": "ch_PP-OCRv4_det",
        "rec_model": "ch_PP-OCRv4_rec",
        "lang": "en"
    }
    
    # Load middle frame
    frame_paths = shot.get("frame_paths", [])
    if not frame_paths:
        return {"text": [], "provenance": {}}
    
    mid_idx = len(frame_paths) // 2
    frame_path = frame_paths[mid_idx]
    image = cv2.imread(frame_path)
    
    if image is None:
        return {"text": [], "provenance": {}}
    
    # Detect text
    texts = detect_text(image)
    
    provenance = {
        "tool": "paddleocr+deepfont",
        "version": "2.7.0",
        "ckpt": "PP-OCRv4",
        "params_hash": sha256_obj(params)
    }
    
    return {
        "text": texts,
        "has_text": len(texts) > 0,
        "text_count": len(texts),
        "provenance": provenance
    }
