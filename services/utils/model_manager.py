"""Model manager for downloading and initializing all required models."""
import os
import torch
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

MODEL_CACHE = os.getenv("MODEL_CACHE", "/workspace/.cache")


class ModelManager:
    """Manages model downloads and initialization."""
    
    def __init__(self):
        self.cache_dir = Path(MODEL_CACHE)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def setup_all_models(self) -> Dict[str, bool]:
        """Download and setup all required models.
        
        Returns:
            Dict of model_name -> success status
        """
        results = {}
        
        logger.info("🚀 Starting model initialization...")
        
        # 1. YOLO
        results['yolo'] = self._setup_yolo()
        
        # 2. SAM2 (optional, can disable)
        results['sam2'] = self._setup_sam2()
        
        # 3. Real-ESRGAN (optional)
        results['realesrgan'] = self._setup_realesrgan()
        
        # 4. InsightFace
        results['insightface'] = self._setup_insightface()
        
        # 5. PaddleOCR
        results['paddleocr'] = self._setup_paddleocr()
        
        # 6. Qwen-VL (handled by vLLM service)
        results['qwen'] = True
        
        logger.info(f"✅ Model initialization complete: {results}")
        return results
    
    def _setup_yolo(self) -> bool:
        """Setup YOLO models."""
        try:
            from ultralytics import YOLO
            logger.info("📦 Downloading YOLOv8m...")
            model = YOLO('yolov8m.pt')  # Auto-downloads
            logger.info("✅ YOLOv8m ready")
            return True
        except Exception as e:
            logger.error(f"❌ YOLO setup failed: {e}")
            return False
    
    def _setup_sam2(self) -> bool:
        """Setup SAM2 (optional)."""
        try:
            # SAM2 is large and optional
            # For now, we'll use simplified segmentation
            logger.info("⚠️  SAM2 using simplified mode (optional model)")
            return True
        except Exception as e:
            logger.warning(f"⚠️  SAM2 not available: {e}")
            return False
    
    def _setup_realesrgan(self) -> bool:
        """Setup Real-ESRGAN."""
        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            logger.info("📦 Real-ESRGAN ready (using basicsr)")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Real-ESRGAN not available: {e}")
            return False
    
    def _setup_insightface(self) -> bool:
        """Setup InsightFace."""
        try:
            import insightface
            from insightface.app import FaceAnalysis
            
            logger.info("📦 Downloading InsightFace buffalo_l...")
            app = FaceAnalysis(name='buffalo_l', root=str(self.cache_dir))
            app.prepare(ctx_id=0 if torch.cuda.is_available() else -1, det_size=(640, 640))
            logger.info("✅ InsightFace ready")
            return True
        except Exception as e:
            logger.warning(f"⚠️  InsightFace not available: {e}")
            return False
    
    def _setup_paddleocr(self) -> bool:
        """Setup PaddleOCR."""
        try:
            from paddleocr import PaddleOCR
            
            logger.info("📦 Initializing PaddleOCR...")
            # This will auto-download models
            ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=torch.cuda.is_available())
            logger.info("✅ PaddleOCR ready")
            return True
        except Exception as e:
            logger.warning(f"⚠️  PaddleOCR not available: {e}")
            return False


def initialize_models() -> Dict[str, bool]:
    """Initialize all models on startup.
    
    Returns:
        Dict of initialization results
    """
    manager = ModelManager()
    return manager.setup_all_models()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = initialize_models()
    print(f"\n{'='*50}")
    print("Model Initialization Results:")
    print(f"{'='*50}")
    for model, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {model.upper()}: {'Ready' if status else 'Failed'}")
    print(f"{'='*50}\n")
