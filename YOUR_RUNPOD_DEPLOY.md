# 🚀 YOUR RunPod Deployment - REAL GUIDE

**Your Pod**: `38tdck85q5uma9`  
**Direct IP**: `149.36.1.250:34106`  
**Status**: Ready to deploy

---

## 🎯 THE REAL PLAN

### What We're Actually Doing:
1. **SSH into YOUR pod** (provided above)
2. **Clone the repo** to `/workspace/framely-eyes`
3. **Let Docker handle EVERYTHING** - no manual installs
4. **Models auto-download** on first run (cached forever)
5. **API runs on port 8000** (your Jupyter is 8888, no conflict)
6. **Process ANY video** - works universally

### What We're NOT Doing:
- ❌ No hardcoded paths
- ❌ No manual model downloads
- ❌ No stupid bash scripts that break
- ❌ No "skeleton" implementations

---

## 📋 Step 1: Connect to YOUR Pod

```bash
# Use THIS command (your actual pod)
ssh root@149.36.1.250 -p 34106 -i ~/.ssh/id_ed25519
```

---

## 📋 Step 2: Setup (5 minutes)

```bash
# Navigate to workspace
cd /workspace

# Clone YOUR repo (replace with actual URL)
git clone https://github.com/YOUR_USERNAME/framely-eyes.git
cd framely-eyes

# That's it. Docker will handle the rest.
```

---

## 🐳 Step 3: Build & Run with Docker

```bash
# Build the image (10-15 min first time, cached after)
docker build -f docker/Dockerfile.runpod -t framely:latest .

# Run it (models download automatically on first start)
docker run -d \
  --name framely \
  --gpus all \
  -p 8000:8000 \
  -p 8001:8001 \
  -v /workspace/framely-eyes:/workspace/framely-eyes \
  -v /workspace/.cache:/workspace/.cache \
  --shm-size=16g \
  --restart unless-stopped \
  framely:latest

# Check logs (models downloading)
docker logs -f framely
```

**What's happening:**
- YOLOv8: Auto-downloads (~50MB)
- InsightFace: Auto-downloads (~500MB)  
- PaddleOCR: Auto-downloads (~200MB)
- Qwen-VL: Downloads via vLLM (~4.5GB)
- **Total wait: 15-20 min ONCE**

---

## ✅ Step 4: Verify It Works

```bash
# Wait for "Application startup complete" in logs
# Then test:

curl http://localhost:8000/health

# Should return:
# {"status":"healthy","gpu_available":true,...}
```

---

## 🎬 Step 5: Process a Video (THE REAL TEST)

```bash
# Analyze ANY video
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "real_test",
    "media_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
  }'

# Check status
watch -n 5 'curl -s http://localhost:8000/status/real_test | jq .'

# Get results (after completion)
curl http://localhost:8000/result/real_test > result.json

# Inspect
cat result.json | jq '.status'
cat result.json | jq '.shots[0].detectors | keys'
```

---

## 🌐 Access from Outside

### Option 1: RunPod Proxy (Easiest)
```
https://38tdck85q5uma9-8000.proxy.runpod.net
```

Test it:
```bash
curl https://38tdck85q5uma9-8000.proxy.runpod.net/health
```

### Option 2: Direct IP (Fastest)
```
http://149.36.1.250:8000
```

**Note**: You need to expose port 8000 in RunPod dashboard if using direct IP.

---

## 🔧 Configuration (NO HARDCODING)

Everything is in `configs/limits.yaml`:

```yaml
# Edit based on YOUR GPU
runtime:
  gpu_semaphore: 2        # Adjust based on VRAM
  qwen_context_max_frames: 12
  frame_stride: 1         # Always 1 for 100% coverage

detect:
  tile:
    size: 512             # Adjust for your GPU
    stride: 256
  superres:
    enabled: true         # Disable if low VRAM
  
audio:
  stoi:
    enabled: true         # Full audio analysis
```

**To apply changes:**
```bash
docker restart framely
```

---

## 📊 Monitor Performance

```bash
# GPU usage
nvidia-smi dmon

# API logs
docker logs -f framely

# Container stats
docker stats framely
```

---

## 🚨 Troubleshooting

### "Out of memory"
```yaml
# Edit configs/limits.yaml
runtime:
  gpu_semaphore: 1      # Reduce concurrency

detect:
  superres:
    enabled: false      # Disable SR
```

Then: `docker restart framely`

### "Models not loading"
```bash
# Check logs
docker logs framely | grep -i error

# Models cache in
ls -lah /workspace/.cache/
```

### "Slow processing"
```bash
# Check GPU
nvidia-smi

# Should show framely processes using GPU
```

---

## 💾 Data Persistence

### Models (Cached Forever)
```
/workspace/.cache/
├── huggingface/  (~4.5GB - Qwen)
├── torch/        (~50MB - YOLO)
└── insightface/  (~500MB - Faces)
```

### Videos & Results
```
/workspace/framely-eyes/store/
└── {video_id}/
    ├── video.mp4
    ├── frames/
    ├── audio.wav
    └── vab.json      # Final output
```

---

## 🎯 REAL Production Usage

### Process Your Videos
```python
import httpx
import asyncio

async def analyze_video(video_url: str):
    async with httpx.AsyncClient() as client:
        # Start analysis
        resp = await client.post(
            "http://localhost:8000/analyze",
            json={"video_id": f"vid_{hash(video_url)}", "media_url": video_url},
            timeout=300
        )
        video_id = resp.json()["video_id"]
        
        # Poll until complete
        while True:
            status = await client.get(f"http://localhost:8000/status/{video_id}")
            if status.json()["state"] == "completed":
                break
            await asyncio.sleep(5)
        
        # Get VAB
        result = await client.get(f"http://localhost:8000/result/{video_id}")
        return result.json()

# Use it
vab = asyncio.run(analyze_video("https://your-video.mp4"))
print(f"Detected {len(vab['shots'])} shots")
print(f"Coverage: {vab['status']['coverage']}")
```

---

## 🔒 Security (Add API Key)

```bash
# Edit docker run command, add:
-e API_KEY=your-secret-key-here

# Restart
docker restart framely
```

Now clients must send:
```bash
curl -H "Authorization: Bearer your-secret-key-here" ...
```

---

## 📈 Scale Up

### Multiple Videos in Parallel
Just send multiple analyze requests - the job queue handles it.

### Multiple Pods
Deploy same setup on multiple pods, use load balancer.

### Bigger GPU
Same Docker image works on ANY GPU - just adjust `gpu_semaphore`.

---

## ✅ VALIDATION

After deployment, verify:

```bash
# 1. GPU detected
nvidia-smi

# 2. Docker running
docker ps | grep framely

# 3. Health check
curl http://localhost:8000/health

# 4. Process test video
curl -X POST http://localhost:8000/analyze \
  -d '{"video_id":"validate","media_url":"https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"}'

# 5. Check result (wait 2-3 min)
curl http://localhost:8000/result/validate | jq '.status.state'
# Should return: "ok"

# 6. Verify all detectors ran
curl http://localhost:8000/result/validate | jq '.shots[0].detectors | keys'
# Should show: ["objects", "faces", "text", "color", "motion", "audio", "transition"]
```

---

## 🎉 YOU'RE LIVE

**Your API**: `https://38tdck85q5uma9-8000.proxy.runpod.net`  
**Status**: Running  
**Ready to**: Process ANY video  

**No more bullshit. This is production.** 🚀
