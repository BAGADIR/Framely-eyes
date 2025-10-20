# Framely-Eyes Quick Start Guide

Get up and running with Framely-Eyes in 5 minutes.

## Prerequisites

- **Docker** with GPU support
- **NVIDIA GPU** with CUDA 12.4+
- **16GB+ VRAM** recommended
- **Linux/WSL2** (Windows users need WSL2)

## Step 1: Start Services (2 min)

```bash
# Clone repository
git clone <your-repo-url>
cd Framely-eyes

# Start all services
docker compose -f docker/docker-compose.yml up --build
```

Wait for:
```
✓ api     - Ready
✓ qwen    - Model loaded
✓ redis   - Connected
```

## Step 2: Test Health (30 sec)

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "gpu_available": true,
  "redis_connected": true,
  "qwen_available": true
}
```

## Step 3: Analyze Video (2 min)

### Option A: Use Public Video
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "demo_001",
    "media_url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
  }'
```

### Option B: Upload Local File
```bash
# First, ingest the file
curl -X POST http://localhost:8000/ingest \
  -F "video_id=local_001" \
  -F "file=@/path/to/your/video.mp4"

# Then analyze
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_id": "local_001"}'
```

## Step 4: Check Status

```bash
# Poll every 5 seconds
watch -n 5 'curl -s http://localhost:8000/status/demo_001 | jq .'
```

Wait for:
```json
{
  "state": "completed",
  "vab_available": true
}
```

## Step 5: Get Results

```bash
# Download VAB
curl http://localhost:8000/result/demo_001 > vab.json

# Inspect with jq
cat vab.json | jq '.status'
cat vab.json | jq '.shots[0]'
cat vab.json | jq '.scenes'
```

## Understanding the Output

### VAB Structure
```json
{
  "schema_version": "1.1.0",
  "status": {
    "state": "ok",
    "coverage": {
      "spatial": {"pixels_covered_pct": 100.0},
      "temporal": {"frames_analyzed_pct": 100.0},
      "audio": {"lufs_trace_pct": 100.0}
    }
  },
  "shots": [
    {
      "shot_id": "sh_000",
      "detectors": {
        "objects": [...],    // YOLO detections
        "faces": [...],      // Face + emotions
        "text": [...],       // OCR results
        "color": {...},      // Color analysis
        "motion": {...},     // Camera motion
        "audio": {...}       // Audio metrics
      },
      "summary": "...",      // Qwen-VL analysis
      "mood": "..."
    }
  ],
  "scenes": [...]            // Grouped shots
}
```

### Key Metrics to Check

**Coverage** (should be near 100%):
```bash
cat vab.json | jq '.status.coverage.temporal.frames_analyzed_pct'
# Expected: 100.0
```

**Objects Detected**:
```bash
cat vab.json | jq '.shots[0].detectors.objects | length'
# Example: 12 objects in first shot
```

**Audio Quality**:
```bash
cat vab.json | jq '.shots[0].detectors.audio.lufs'
# Example: -14.2 (near target of -14.0 LUFS)
```

## Common Issues

### GPU Not Available
```bash
# Check NVIDIA driver
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.4.1-base nvidia-smi
```

### Services Not Starting
```bash
# Check logs
docker compose -f docker/docker-compose.yml logs api
docker compose -f docker/docker-compose.yml logs qwen

# Restart services
docker compose -f docker/docker-compose.yml restart
```

### Analysis Failing
```bash
# Check detailed error
curl http://localhost:8000/status/demo_001 | jq '.message'

# Check VAB for risks
cat vab.json | jq '.risks'
```

### Out of Memory
```bash
# Edit configs/limits.yaml
runtime:
  gpu_semaphore: 1          # Reduce from 2 to 1
  
ablation:
  no_sr: true               # Disable super-resolution
```

## Next Steps

### Run Full Test Suite
```bash
bash scripts/smoke_test.sh
```

### Customize Configuration
```bash
vim configs/limits.yaml

# Change detection parameters
# Adjust coverage thresholds
# Enable/disable features
```

### Integrate with Your App
```python
import httpx
import asyncio

async def analyze_video(video_url: str):
    async with httpx.AsyncClient() as client:
        # Start analysis
        response = await client.post(
            "http://localhost:8000/analyze",
            json={
                "video_id": "my_video",
                "media_url": video_url
            }
        )
        print(f"Job started: {response.json()}")
        
        # Poll status
        while True:
            status = await client.get("http://localhost:8000/status/my_video")
            state = status.json()["state"]
            
            if state == "completed":
                break
            elif state == "failed":
                raise Exception("Analysis failed")
            
            await asyncio.sleep(5)
        
        # Get results
        vab = await client.get("http://localhost:8000/result/my_video")
        return vab.json()

# Run
asyncio.run(analyze_video("https://example.com/video.mp4"))
```

### Explore Advanced Features
```bash
# Enable ablations
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test_002",
    "media_url": "...",
    "ablations": {
      "no_sr": true,
      "light_audio": true
    }
  }'
```

## Performance Tips

### Faster Analysis
- Use smaller videos for testing
- Reduce `qwen_context_max_frames` in config
- Disable super-resolution for high-res videos

### Better Quality
- Increase `tile_size` for larger objects
- Enable all detectors (no ablations)
- Use higher-res source videos

### Resource Management
- Lower `gpu_semaphore` if OOM occurs
- Process videos sequentially
- Clean up store/ directory periodically

## Support

- **Documentation**: Check `README.md` and `ARCHITECTURE.md`
- **Issues**: Open GitHub issue with logs
- **Contributions**: See `CONTRIBUTING.md`

Happy analyzing! 👁️✨
