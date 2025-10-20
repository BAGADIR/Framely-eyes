# 🚀 RunPod Deployment Guide

**Complete guide for deploying Framely-Eyes on RunPod.io**

---

## 📋 RunPod Template Setup

### Step 1: Create Pod

**GPU Selection:**
- **Minimum**: RTX 4090 (24GB VRAM)
- **Recommended**: RTX A6000 (48GB VRAM)
- **Optimal**: A100 (40GB/80GB VRAM)

**Container Settings:**
- **Container Image**: `runpod/pytorch:2.1.0-py3.10-cuda12.1.1-devel-ubuntu22.04`
- **Container Disk**: 50GB minimum
- **Volume Disk**: 100GB+ for models and videos

---

## 🔧 Quick Deploy (Automated)

### Option A: One-Click Deploy

```bash
# SSH into your RunPod instance
ssh root@<your-pod-id>.ssh.runpod.io -i ~/.ssh/id_ed25519

# Run automated setup
curl -sSL https://raw.githubusercontent.com/<your-repo>/main/scripts/runpod_deploy.sh | bash
```

### Option B: Manual Deploy

**1. Clone Repository**
```bash
cd /workspace
git clone <your-repo-url> framely-eyes
cd framely-eyes
```

**2. Install Dependencies**
```bash
# Install system packages
apt-get update && apt-get install -y ffmpeg redis-server libsndfile1

# Install Python packages
pip install -r requirements.txt
pip install -r requirements-models.txt
```

**3. Initialize Models**
```bash
# This downloads all models (takes 10-15 min)
python3 -m services.utils.model_manager
```

**4. Configure**
```bash
# Copy and edit config
cp configs/settings.example.env configs/settings.env
nano configs/settings.env

# Set these for RunPod:
# STORE_PATH=/workspace/framely-eyes/store
# MODEL_CACHE=/workspace/.cache
# REDIS_HOST=127.0.0.1
```

**5. Start Services**
```bash
# Start Redis
redis-server --daemonize yes

# Start Qwen-VL (in background)
python3 -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-VL-7B-Instruct \
    --quantization awq \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.5 \
    --port 8001 \
    --host 0.0.0.0 &

# Wait for Qwen to load (2-3 min)
sleep 180

# Start Framely API
uvicorn services.api.api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1
```

**6. Test**
```bash
# Get your RunPod public IP
export POD_IP=$(curl -s https://ipv4.icanhazip.com)

# Test health
curl http://$POD_IP:8000/health

# Test analysis
curl -X POST http://$POD_IP:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test_001",
    "media_url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
  }'
```

---

## 🐳 Docker Deploy (Recommended)

**Build and Run:**
```bash
cd /workspace/framely-eyes

# Build RunPod image
docker build -f docker/Dockerfile.runpod -t framely-runpod:latest .

# Run all-in-one container
docker run -d \
  --name framely \
  --gpus all \
  -p 8000:8000 \
  -v /workspace/framely-eyes:/workspace/framely-eyes \
  -v /workspace/.cache:/workspace/.cache \
  --shm-size=16g \
  framely-runpod:latest

# Check logs
docker logs -f framely
```

**Or use Docker Compose:**
```bash
docker compose -f docker/docker-compose.runpod.yml up -d
```

---

## ⚡ Performance Optimization

### GPU Memory Allocation

**RTX 4090 (24GB)**
```yaml
# configs/limits.yaml
runtime:
  gpu_semaphore: 1
  qwen_context_max_frames: 8

detect:
  superres:
    enabled: false  # Disable SR to save memory
```

**RTX A6000 (48GB)**
```yaml
runtime:
  gpu_semaphore: 2
  qwen_context_max_frames: 12

detect:
  superres:
    enabled: true
```

**A100 (80GB)**
```yaml
runtime:
  gpu_semaphore: 3
  qwen_context_max_frames: 16

detect:
  superres:
    enabled: true
  tile:
    size: 640  # Larger tiles
```

---

## 📊 Model Download Times & Sizes

| Model | Size | Download Time (1Gbps) | Notes |
|-------|------|----------------------|-------|
| YOLOv8m | 50MB | 5 sec | Auto-downloads |
| InsightFace | 500MB | 45 sec | Auto-downloads |
| PaddleOCR | 200MB | 20 sec | Auto-downloads |
| Real-ESRGAN | 65MB | 6 sec | Manual setup |
| Qwen-VL-7B-AWQ | 4.5GB | 6 min | vLLM downloads |
| **Total** | **~5.3GB** | **~8 min** | First run only |

**Pro Tip:** Models are cached in `/workspace/.cache`, so subsequent pod restarts are fast!

---

## 🔒 RunPod-Specific Security

### Expose API Publicly

**1. Use RunPod HTTP Service**
```bash
# RunPod automatically exposes port 8000
# Access via: https://<pod-id>-8000.proxy.runpod.net
```

**2. Add Authentication**
```python
# In services/api/router.py
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("API_KEY", "your-secret-key"):
        raise HTTPException(401, "Invalid API key")

# Add to endpoints:
@router.post("/analyze", dependencies=[Depends(verify_api_key)])
```

**3. Set API Key**
```bash
# In configs/settings.env
API_KEY=your-super-secret-key-here-change-this
```

---

## 💾 Data Persistence

### Save Models to Volume
```bash
# Link cache to persistent volume
mkdir -p /workspace/.cache
ln -s /workspace/.cache /root/.cache

# Now models persist across pod restarts
```

### Save VABs to Volume
```bash
# Already configured in settings.env
STORE_PATH=/workspace/framely-eyes/store

# VABs are automatically saved to persistent volume
```

---

## 🔄 Auto-Restart on Failure

**Create Systemd Service:**
```bash
cat > /etc/systemd/system/framely.service <<'EOF'
[Unit]
Description=Framely-Eyes Video Analysis
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace/framely-eyes
ExecStart=/workspace/framely-eyes/docker/runpod_start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl enable framely
systemctl start framely
```

---

## 📈 Monitoring on RunPod

### Check GPU Usage
```bash
watch -n 1 nvidia-smi
```

### Check API Logs
```bash
tail -f /var/log/framely.log
# or if using Docker:
docker logs -f framely
```

### Monitor Disk Space
```bash
df -h /workspace
```

---

## 🚨 Troubleshooting

### "CUDA out of memory"
```bash
# Reduce GPU usage in configs/limits.yaml
runtime:
  gpu_semaphore: 1

# Or use ablations:
curl -X POST http://localhost:8000/analyze \
  -d '{"video_id":"test","media_url":"...","ablations":{"no_sr":true}}'
```

### "Models not found"
```bash
# Re-run model initialization
python3 -m services.utils.model_manager

# Check cache directory
ls -lah /workspace/.cache/
```

### "Redis connection failed"
```bash
# Start Redis
redis-server --daemonize yes

# Verify
redis-cli ping  # Should return PONG
```

---

## 💰 Cost Optimization

### Billing Recommendations

**Development/Testing:**
- RTX 4090: ~$0.40/hr
- Run only when actively testing
- Stop pod when not in use

**Production:**
- A6000: ~$0.80/hr  
- Keep running 24/7
- ~$580/month

**Scaling:**
- Use multiple pods behind load balancer
- Each pod processes videos independently

---

## 🎯 Quick Start Checklist

- [ ] Create RunPod pod (RTX 4090+)
- [ ] SSH into pod
- [ ] Clone repository
- [ ] Install dependencies
- [ ] Initialize models (10 min)
- [ ] Configure settings.env
- [ ] Start services
- [ ] Test with sample video
- [ ] Expose public URL
- [ ] Add API authentication
- [ ] Monitor GPU usage
- [ ] Set up auto-restart

---

## 📞 RunPod Support

### Common Pod Issues

**Pod won't start:**
- Check GPU availability in RunPod dashboard
- Try different GPU type
- Verify Docker image

**Can't access API:**
- Check RunPod proxy URL: `https://<pod-id>-8000.proxy.runpod.net`
- Verify port 8000 is exposed
- Check firewall settings

**Slow performance:**
- Monitor GPU with `nvidia-smi`
- Check if GPU is actually being used
- Tune `configs/limits.yaml`

---

## ✅ Verification

**After setup, verify:**

```bash
# 1. GPU detected
nvidia-smi

# 2. Models loaded
ls -lah /workspace/.cache/

# 3. Services running
curl http://localhost:8000/health

# 4. Process test video
curl -X POST http://localhost:8000/analyze \
  -d '{"video_id":"verify","media_url":"https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"}'

# 5. Get results (wait 2-3 min)
curl http://localhost:8000/result/verify | jq '.status.state'
# Should return: "ok"
```

---

**✨ You're ready to analyze videos on RunPod! 🚀**
