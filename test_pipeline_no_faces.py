#!/usr/bin/env python3
"""Quick test for Framely-Eyes pipeline without face detection."""
import asyncio
import subprocess
from pathlib import Path

VIDEO_URL = "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
VIDEO_PATH = "/workspace/test_video.mp4"

async def main():
    print("=" * 70)
    print("FRAMELY-EYES PIPELINE TEST (NO FACES)")
    print("=" * 70)
    
    # Download test video
    if not Path(VIDEO_PATH).exists():
        print("\n📥 Downloading test video...")
        subprocess.run(["wget", VIDEO_URL, "-O", VIDEO_PATH, "-q"])
        print("✅ Video downloaded")
    else:
        print(f"✅ Video already exists: {VIDEO_PATH}")
    
    # Run analysis with face detection disabled
    print("\n🚀 Starting analysis...")
    from services.orchestrator.orchestrator import run_analysis
    
    # Disable face detection to avoid CUDA PTX error
    ablations = {"no_faces": True}
    
    job_id = await run_analysis("test002", VIDEO_PATH, ablations=ablations)
    
    print(f"\n✅ COMPLETE! Job: {job_id}")
    print(f"\n📄 Check output:")
    print(f"   /workspace/Framely-eyes/store/test002/vab.json")
    
    # Quick validation
    from services.utils.io import load_vab
    vab = load_vab("test002", "/workspace/Framely-eyes/store")
    
    if vab:
        shots = vab.get("shots", [])
        print(f"\n📊 Results:")
        print(f"   Shots detected: {len(shots)}")
        if shots:
            detectors = shots[0].get("detectors", {})
            objects = detectors.get("objects", [])
            text = detectors.get("text", [])
            print(f"   Objects detected: {len(objects)}")
            print(f"   Text regions: {len(text)}")
            
            # Show first few objects
            if objects:
                print(f"\n🎯 First 3 objects:")
                for i, obj in enumerate(objects[:3]):
                    track_id = obj.get("track_id", "N/A")
                    motion = obj.get("motion", {})
                    moving = motion.get("moving", False)
                    print(f"   {i+1}. {obj['label']} (conf: {obj['conf']:.2f}, track_id: {track_id}, moving: {moving})")

if __name__ == "__main__":
    asyncio.run(main())
