#!/usr/bin/env python3
"""Verify all required packages are installed."""

import sys

def check_imports():
    """Test import of all critical packages."""
    results = {}
    
    # Core
    packages = {
        "cv2": "opencv-python",
        "numpy": "numpy",
        "torch": "pytorch",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        
        # Vision Models
        "ultralytics": "ultralytics (YOLO)",
        "insightface": "insightface",
        "paddleocr": "paddleocr",
        "basicsr.archs": "basicsr (Real-ESRGAN)",
        "realesrgan.archs": "realesrgan",
        
        # Audio
        "librosa": "librosa",
        "essentia": "essentia",
        "soundfile": "soundfile",
        "whisper": "openai-whisper",
        
        # ML/DL
        "tensorflow": "tensorflow",
        "timm": "timm",
        
        # Utils
        "redis": "redis",
        "qdrant_client": "qdrant-client",
    }
    
    print("=" * 60)
    print("VERIFYING PACKAGE INSTALLATIONS")
    print("=" * 60)
    
    for module, name in packages.items():
        try:
            __import__(module)
            results[name] = "✅ INSTALLED"
            print(f"✅ {name:30} OK")
        except ImportError as e:
            results[name] = f"❌ MISSING: {e}"
            print(f"❌ {name:30} MISSING")
    
    print("\n" + "=" * 60)
    
    # Check for packages that need special verification
    print("\nSPECIAL CHECKS:")
    print("=" * 60)
    
    # CUDA
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"{'✅' if cuda_available else '⚠️ '} CUDA Available: {cuda_available}")
        if cuda_available:
            print(f"  └─ GPU: {torch.cuda.get_device_name(0)}")
            print(f"  └─ CUDA Version: {torch.version.cuda}")
    except Exception as e:
        print(f"❌ CUDA check failed: {e}")
    
    # SAM2 (installed separately)
    try:
        import sam2
        print("✅ SAM2 (Segment Anything 2) - INSTALLED")
    except ImportError:
        print("⚠️  SAM2 - NOT INSTALLED (install with: pip install git+https://github.com/facebookresearch/segment-anything-2.git)")
    
    # Qwen-VL (external service)
    print("ℹ️  Qwen-VL - External vLLM service (not pip package)")
    print("  └─ Expects service at: http://qwen:8000/v1")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    missing = [k for k, v in results.items() if "MISSING" in v]
    if missing:
        print(f"❌ {len(missing)} package(s) missing:")
        for pkg in missing:
            print(f"   - {pkg}")
        return 1
    else:
        print("✅ All required packages installed!")
        return 0

if __name__ == "__main__":
    sys.exit(check_imports())
