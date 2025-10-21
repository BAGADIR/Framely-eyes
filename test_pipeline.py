#!/usr/bin/env python3
"""Quick test for Framely-Eyes pipeline."""
import asyncio
import subprocess
from pathlib import Path

VIDEO_URL = "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
VIDEO_PATH = "/workspace/test_video.mp4"

async def main():
    print("=" * 70)
    print("FRAMELY-EYES PIPELINE TEST")
    print("=" * 70)
    
    # Download test video
    if not Path(VIDEO_PATH).exists():
        print("\n📥 Downloading test video...")
        subprocess.run(["wget", VIDEO_URL, "-O", VIDEO_PATH, "-q"])
        print("✅ Video downloaded")
    else:
        print(f"✅ Video already exists: {VIDEO_PATH}")
    
    # Run analysis
    print("\n🚀 Starting analysis...")
    from services.orchestrator.orchestrator import run_analysis
    
    job_id = await run_analysis("test001", VIDEO_PATH, ablations=None)
    
    print(f"\n✅ COMPLETE! Job: {job_id}")
    print(f"\n📄 Check output:")
    print(f"   /workspace/Framely-eyes/store/test001/vab.json")
    
    # Quick validation
    from services.utils.io import load_vab
    vab = load_vab("test001", "/workspace/Framely-eyes/store")
    
    if vab:
        shots = vab.get("shots", [])
        print(f"\n📊 Results:")
        print(f"   Shots detected: {len(shots)}")
        if shots:
            objects = shots[0].get("detectors", {}).get("objects", [])
            print(f"   Objects in shot 0: {len(objects)}")

if __name__ == "__main__":
    asyncio.run(main())
