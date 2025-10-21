#!/usr/bin/env python3
"""Quick test of basicsr and realesrgan imports."""

try:
    from basicsr.archs.rrdbnet_arch import RRDBNet
    print("OK: basicsr works")
except Exception as e:
    print(f"FAIL: basicsr - {e}")

try:
    from realesrgan import RealESRGANer
    print("OK: realesrgan works")
except Exception as e:
    print(f"FAIL: realesrgan - {e}")
