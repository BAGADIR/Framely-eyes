# Troubleshooting Guide

Common issues and solutions for Framely-Eyes.

---

## 🚨 Common Issues

### 1. GPU Not Available

**Symptom:**
```json
{
  "gpu_available": false
}
```

**Solutions:**

**A. Check NVIDIA Driver**
```bash
nvidia-smi
```
Expected: Driver version and GPU info

**B. Install NVIDIA Container Toolkit**
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

**C. Test Docker GPU Access**
```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base nvidia-smi
```

**D. Update docker-compose.yml (if needed)**
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

---

### 2. Qwen Service Not Starting

**Symptom:**
```
qwen_1  | RuntimeError: CUDA out of memory
```

**Solutions:**

**A. Reduce GPU Memory Utilization**
Edit `docker/docker-compose.yml`:
```yaml
qwen:
  command: >
    --model Qwen/Qwen2.5-VL-7B-Instruct
    --quantization awq
    --max-model-len 4096        # Reduced from 8192
    --gpu-memory-utilization 0.7  # Reduced from 0.9
```

**B. Use Smaller Model**
```yaml
--model Qwen/Qwen2-VL-2B-Instruct
```

**C. CPU Fallback (Slow)**
```yaml
environment:
  - CUDA_VISIBLE_DEVICES=-1
```

---

### 3. Analysis Job Stuck

**Symptom:**
```json
{
  "state": "processing",
  "progress": 30.0
}
```

**Solutions:**

**A. Check Logs**
```bash
docker compose -f docker/docker-compose.yml logs api
docker compose -f docker/docker-compose.yml logs qwen
```

**B. Check GPU Usage**
```bash
watch -n 1 nvidia-smi
```

**C. Check Redis Connection**
```bash
docker compose -f docker/docker-compose.yml exec redis redis-cli ping
# Expected: PONG
```

**D. Restart Job**
```bash
# Stop services
docker compose -f docker/docker-compose.yml restart

# Clear Redis job
docker compose -f docker/docker-compose.yml exec redis redis-cli DEL job:video_id
```

---

### 4. Out of Memory (OOM) Errors

**Symptom:**
```
RuntimeError: CUDA out of memory
```

**Solutions:**

**A. Automatic Fallbacks (Already Implemented)**
System automatically:
1. Disables SAM2
2. Disables Super-Resolution
3. Reduces Qwen context

**B. Manual Configuration**
Edit `configs/limits.yaml`:
```yaml
runtime:
  gpu_semaphore: 1  # Reduce from 2

ablation:
  no_sr: true      # Disable super-resolution
  no_tiling: false
  light_audio: true

detect:
  superres:
    enabled: false
```

**C. Process Videos Sequentially**
```bash
# Don't start multiple analyses simultaneously
```

**D. Use Smaller Input Videos**
```bash
# Resize video before analysis
ffmpeg -i input.mp4 -vf scale=1280:720 -c:a copy output.mp4
```

---

### 5. Redis Connection Failed

**Symptom:**
```json
{
  "redis_connected": false
}
```

**Solutions:**

**A. Check Redis Status**
```bash
docker compose -f docker/docker-compose.yml ps redis
```

**B. Restart Redis**
```bash
docker compose -f docker/docker-compose.yml restart redis
```

**C. Check Port Conflict**
```bash
netstat -an | grep 6379
# If occupied, change port in docker-compose.yml
```

**D. Verify Network**
```bash
docker compose -f docker/docker-compose.yml exec api ping redis
```

---

### 6. File Upload Fails

**Symptom:**
```
413 Request Entity Too Large
```

**Solutions:**

**A. Increase Size Limit**
Edit `configs/settings.example.env`:
```bash
MAX_VIDEO_MB=2000  # Increase from 1000
```

**B. Check File Size**
```bash
ls -lh video.mp4
```

**C. Use URL Instead**
```bash
# Upload to file hosting service first
curl -X POST http://localhost:8000/analyze \
  -d '{"video_id":"test","media_url":"https://..."}'
```

---

### 7. Unsupported Media Type

**Symptom:**
```
415 Unsupported media type
```

**Solutions:**

**A. Check MIME Type**
```bash
file --mime-type video.mp4
# Expected: video/mp4
```

**B. Convert Video**
```bash
ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4
```

**C. Add MIME Type to Whitelist**
Edit `configs/settings.example.env`:
```bash
MIME_WHITELIST=video/mp4,video/quicktime,video/x-matroska,video/avi
```

---

### 8. Model Weights Not Found

**Symptom:**
```
FileNotFoundError: yolov8m.pt not found
```

**Solutions:**

**A. Download YOLO Weights**
```python
from ultralytics import YOLO
model = YOLO('yolov8m.pt')  # Auto-downloads
```

**B. Place in Correct Directory**
```bash
mkdir -p ~/.cache/torch/hub/checkpoints/
# Place model files here
```

**C. Update Model Paths**
Edit `configs/model_paths.yaml`:
```yaml
yolo:
  checkpoint: /path/to/yolov8m.pt
```

---

### 9. Slow Performance

**Symptom:**
Analysis takes > 10 minutes per minute of video

**Solutions:**

**A. Check GPU Utilization**
```bash
nvidia-smi dmon
# GPU utilization should be 80-100%
```

**B. Optimize Configuration**
```yaml
# configs/limits.yaml
runtime:
  frame_stride: 2  # Analyze every 2nd frame instead of every frame

detect:
  two_pass:
    enabled: false  # Disable tiled detection
  superres:
    enabled: false  # Disable super-resolution

audio:
  stoi:
    enabled: false  # Skip STOI calculation
```

**C. Use Smaller Model**
```yaml
yolo:
  checkpoint: yolov8n.pt  # Nano version (faster)
```

**D. Reduce Qwen Context**
```yaml
runtime:
  qwen_context_max_frames: 6  # Reduce from 12
```

---

### 10. Empty VAB or Missing Detections

**Symptom:**
```json
{
  "shots": [],
  "scenes": []
}
```

**Solutions:**

**A. Check Video Validity**
```bash
ffprobe video.mp4
# Check codec, resolution, duration
```

**B. Check Frame Extraction**
```bash
ls -la store/video_id/frames/
# Should contain frame_*.jpg files
```

**C. Check Logs for Errors**
```bash
docker compose -f docker/docker-compose.yml logs api | grep ERROR
```

**D. Verify Shot Detection**
```python
from scenedetect import detect, ContentDetector
scenes = detect('video.mp4', ContentDetector())
print(f"Detected {len(scenes)} scenes")
```

---

### 11. Coverage Below Threshold

**Symptom:**
```json
{
  "status": {
    "state": "degraded",
    "reasons": ["low_temporal_coverage"]
  }
}
```

**Solutions:**

**A. Check Frame Stride**
```yaml
# configs/limits.yaml
runtime:
  frame_stride: 1  # Must be 1 for 100% coverage
```

**B. Lower Thresholds**
```yaml
coverage_thresholds:
  frames_analyzed_pct: 95  # Reduce from 99
  stoi_pct: 80            # Reduce from 90
```

**C. Fix Frame Extraction**
Check that all frames are being saved properly in prep.py

---

### 12. Docker Build Fails

**Symptom:**
```
ERROR: failed to solve
```

**Solutions:**

**A. Clean Docker Cache**
```bash
docker system prune -a
docker compose -f docker/docker-compose.yml build --no-cache
```

**B. Check Disk Space**
```bash
df -h
```

**C. Increase Docker Memory**
```bash
# Docker Desktop: Settings → Resources → Memory (16GB+)
```

**D. Check Base Image**
```dockerfile
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
# Ensure this image exists and is accessible
```

---

## 🔧 Debugging Commands

### View Real-time Logs
```bash
# All services
docker compose -f docker/docker-compose.yml logs -f

# Specific service
docker compose -f docker/docker-compose.yml logs -f api

# Last 100 lines
docker compose -f docker/docker-compose.yml logs --tail=100 api
```

### Inspect Container
```bash
docker compose -f docker/docker-compose.yml exec api bash
cd /app
python -c "import torch; print(torch.cuda.is_available())"
```

### Check GPU Memory
```bash
watch -n 1 'nvidia-smi --query-gpu=memory.used,memory.total --format=csv'
```

### Monitor Redis
```bash
docker compose -f docker/docker-compose.yml exec redis redis-cli
> KEYS *
> HGETALL job:video_id
```

### Test Detector Individually
```python
from services.detectors import yolo
import cv2

shot = {
    "shot_id": "test",
    "frame_paths": ["path/to/frame.jpg"]
}
cfg = {"detect": {"tile": {"size": 512}}}

result = yolo.detect(shot, cfg)
print(result)
```

---

## 📊 Performance Profiling

### Enable Verbose Logging
```python
# In api.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Profile GPU Memory
```bash
# Terminal 1: Monitor GPU
watch -n 1 nvidia-smi

# Terminal 2: Run analysis
curl -X POST http://localhost:8000/analyze -d '{"video_id":"test","media_url":"..."}'
```

### Check Metrics
```bash
curl http://localhost:8000/result/video_id | jq '.video.metrics'
```

---

## 🆘 Getting Help

### 1. Gather Information
```bash
# System info
uname -a
nvidia-smi
docker --version

# Logs
docker compose -f docker/docker-compose.yml logs > logs.txt

# VAB (if generated)
curl http://localhost:8000/result/video_id > vab.json
```

### 2. Check Documentation
- `README.md` - Overview and quick start
- `ARCHITECTURE.md` - Technical details
- `QUICKSTART.md` - Step-by-step guide
- `API_EXAMPLES.md` - API usage

### 3. Open Issue
Include:
- System info (OS, GPU, CUDA version)
- Error logs
- Steps to reproduce
- Expected vs actual behavior

---

## 💡 Best Practices

### Before Analysis
1. Test with small video first (< 10 seconds)
2. Check GPU availability
3. Monitor disk space
4. Verify all services are healthy

### During Analysis
1. Monitor GPU usage
2. Watch logs for errors
3. Don't start multiple jobs simultaneously (unless scaled)

### After Analysis
1. Validate VAB structure
2. Check coverage metrics
3. Review risks
4. Clean up store/ directory periodically

---

## 🎯 Quick Fixes Checklist

- [ ] GPU available? → `nvidia-smi`
- [ ] Services running? → `docker ps`
- [ ] Redis connected? → `curl http://localhost:8000/health`
- [ ] Disk space? → `df -h`
- [ ] Logs clean? → `docker compose logs`
- [ ] Config valid? → Check YAML syntax
- [ ] Video valid? → `ffprobe video.mp4`
- [ ] Ports free? → `netstat -an | grep 8000`

---

**Still having issues?** Check the logs first, they usually contain the answer! 🔍
