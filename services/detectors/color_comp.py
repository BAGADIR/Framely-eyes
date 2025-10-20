"""Color and composition analysis using OpenCV."""
import cv2
import numpy as np
from typing import Dict, Any, List
from sklearn.cluster import KMeans
from services.utils.hashing import sha256_obj


def extract_dominant_colors(image: np.ndarray, n_colors: int = 5) -> List[List[int]]:
    """Extract dominant colors using k-means clustering.
    
    Args:
        image: Input image (BGR)
        n_colors: Number of dominant colors to extract
        
    Returns:
        List of RGB colors
    """
    # Reshape image to list of pixels
    pixels = image.reshape(-1, 3)
    
    # Convert BGR to RGB
    pixels = cv2.cvtColor(pixels.reshape(1, -1, 3), cv2.COLOR_BGR2RGB).reshape(-1, 3)
    
    # Apply k-means
    kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    kmeans.fit(pixels)
    
    colors = kmeans.cluster_centers_.astype(int).tolist()
    return colors


def compute_brightness(image: np.ndarray) -> float:
    """Compute average brightness.
    
    Args:
        image: Input image
        
    Returns:
        Brightness value [0, 1]
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray) / 255.0)


def compute_contrast(image: np.ndarray) -> float:
    """Compute contrast using standard deviation.
    
    Args:
        image: Input image
        
    Returns:
        Contrast value
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(np.std(gray))


def compute_saturation(image: np.ndarray) -> float:
    """Compute average saturation.
    
    Args:
        image: Input image (BGR)
        
    Returns:
        Saturation value [0, 1]
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    return float(np.mean(hsv[:, :, 1]) / 255.0)


def analyze_composition(image: np.ndarray) -> Dict[str, Any]:
    """Analyze composition using rule of thirds.
    
    Args:
        image: Input image
        
    Returns:
        Composition analysis
    """
    h, w = image.shape[:2]
    
    # Divide into 3x3 grid
    grid_h = h // 3
    grid_w = w // 3
    
    # Compute interest in each grid cell (using edge detection)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    grid_interest = []
    for i in range(3):
        row_interest = []
        for j in range(3):
            cell = edges[i*grid_h:(i+1)*grid_h, j*grid_w:(j+1)*grid_w]
            interest = float(np.sum(cell) / (grid_h * grid_w * 255))
            row_interest.append(round(interest, 3))
        grid_interest.append(row_interest)
    
    return {
        "grid_interest": grid_interest,
        "rule_of_thirds_score": float(np.mean([grid_interest[0][2], grid_interest[2][0]]))
    }


def detect(shot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze color and composition of a shot.
    
    Args:
        shot: Shot metadata with frame paths
        cfg: Configuration dictionary
        
    Returns:
        Color and composition analysis with provenance
    """
    params = {
        "n_colors": 5,
        "analysis": ["brightness", "contrast", "saturation", "composition"]
    }
    
    # Load middle frame
    frame_paths = shot.get("frame_paths", [])
    if not frame_paths:
        return {"color": {}, "provenance": {}}
    
    mid_idx = len(frame_paths) // 2
    frame_path = frame_paths[mid_idx]
    image = cv2.imread(frame_path)
    
    if image is None:
        return {"color": {}, "provenance": {}}
    
    # Analyze color and composition
    result = {
        "dominant_colors": extract_dominant_colors(image, params["n_colors"]),
        "brightness": round(compute_brightness(image), 3),
        "contrast": round(compute_contrast(image), 3),
        "saturation": round(compute_saturation(image), 3),
        "composition": analyze_composition(image)
    }
    
    provenance = {
        "tool": "opencv_color_comp",
        "version": "4.8.0",
        "params_hash": sha256_obj(params)
    }
    
    return {
        "color": result,
        "provenance": provenance
    }
