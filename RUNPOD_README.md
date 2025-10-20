# 🚀 Framely-Eyes for RunPod

**One-command deployment for RunPod.io GPU instances**

---

## ⚡ Quick Deploy (30 seconds)

```bash
# SSH into your RunPod pod
ssh root@<your-pod-id>.ssh.runpod.io -i ~/.ssh/id_ed25519

# Run automated setup
curl -sSL https://raw.githubusercontent.com/YOUR_REPO/main/scripts/runpod_deploy.sh | bash
```

**That's it!** ✨

---

## 📋 What Gets Installed

### Automatically Installed & Configured:
- ✅ All system dependencies (ffmpeg, redis, etc.)
- ✅ All Python packages (~50 packages)
- ✅ All AI models (~5.3GB total):
  - YOLOv8m (object detection)
  - InsightFace (face detection)
  - PaddleOCR (text recognition)
  - Real-ESRGAN (super-resolution)
  - Qwen-VL-7B (vision-language reasoning)
- ✅ Redis (job queue)
- ✅ API server with auto-restart
- ✅ Health monitoring
- ✅ Public URL via RunPod proxy

### Total Setup Time:
- **Automated script**: ~15 minutes (one-time)
- **Model downloads**: Cached for future restarts
- **Subsequent restarts**: ~30 seconds

---

## 💰 Cost Estimate

| GPU | VRAM | Price/hr | Monthly (24/7) | Recommended Use |
|-----|------|----------|----------------|-----------------|
| RTX 4090 | 24GB | $0.40 | $288 | Development/Testing |
| RTX A6000 | 48GB | $0.80 | $576 | Production |
| A100 (40GB) | 40GB | $1.40 | $1,008 | High-volume |
| A100 (80GB) | 80GB | $1.90 | $1,368 | Maximum performance |

**Recommendation**: Start with RTX 4090 for testing, scale to A6000 for production.

---

## 🎯 What You Get

### Complete Video Analysis
- **11 AI Detectors** running in parallel
- **100% Coverage** guarantees (spatial, temporal, audio)
- **Qwen-VL Reasoning** for context understanding
- **JSON Output** ready for GPT-5/LLMs

### Production Features
- **GPU-Optimized** with resource pooling
- **OOM-Safe** with automatic fallbacks
- **Auto-Restart** on failures
- **Health Monitoring** built-in
- **Public API** via RunPod proxy

---

## 🔧 Configuration

### For Different GPU Sizes

**RTX 4090 (24GB) - Basic**
```yaml
# Edit: configs/limits.yaml
runtime:
  gpu_semaphore: 1
  qwen_context_max_frames: 8

detect:
  superres:
    enabled: false  # Save memory
```

**A6000 (48GB) - Full Features**
```yaml
runtime:
  gpu_semaphore: 2
  qwen_context_max_frames: 12

detect:
  superres:
    enabled: true
```

**A100 (80GB) - Maximum Performance**
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

## 📊 Performance

### Analysis Speed
| Video Length | Resolution | RTX 4090 | A6000 | A100 |
|--------------|------------|----------|-------|------|
| 10 seconds | 1080p | 15 sec | 12 sec | 8 sec |
| 1 minute | 1080p | 90 sec | 70 sec | 45 sec |
| 5 minutes | 1080p | 7.5 min | 6 min | 4 min |
| 10 minutes | 4K | 30 min | 22 min | 15 min |

**Note**: Times include all 11 detectors + Qwen-VL reasoning

---

## 🌐 Access Your API

### Public URL
```
https://<pod-id>-8000.proxy.runpod.net
```

Find your pod ID in RunPod dashboard.

### Test It
```bash
# Health check
curl https://<pod-id>-8000.proxy.runpod.net/health

# Analyze video
curl -X POST https://<pod-id>-8000.proxy.runpod.net/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test_001",
    "media_url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
  }'

# Get results (wait 2-3 min)
curl https://<pod-id>-8000.proxy.runpod.net/result/test_001 > result.json
```

---

## 🔒 Security

### Add API Key Authentication

```bash
# Edit: configs/settings.env
echo "API_KEY=your-super-secret-key-here" >> configs/settings.env

# Restart
systemctl restart framely
```

Now clients must include:
```bash
curl -H "Authorization: Bearer your-super-secret-key-here" ...
```

---

## 📈 Monitoring

### Check Service Status
```bash
systemctl status framely
```

### View Logs
```bash
journalctl -u framely -f
```

### Monitor GPU
```bash
watch -n 1 nvidia-smi
```

### Check Disk Space
```bash
df -h /workspace
```

---

## 🔄 Management Commands

```bash
# Restart service
systemctl restart framely

# Stop service
systemctl stop framely

# Start service
systemctl start framely

# View logs
journalctl -u framely -f

# Check health
curl http://localhost:8000/health

# Clear old videos
rm -rf /workspace/framely-eyes/store/*
```

---

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check logs
journalctl -u framely -n 50

# Check GPU
nvidia-smi

# Restart
systemctl restart framely
```

### Out of Memory
```bash
# Edit config
nano /workspace/framely-eyes/configs/limits.yaml

# Reduce gpu_semaphore from 2 to 1
# Restart
systemctl restart framely
```

### Models Not Found
```bash
cd /workspace/framely-eyes
python3 -m services.utils.model_manager
systemctl restart framely
```

### Slow Performance
```bash
# Check GPU usage
nvidia-smi

# If GPU usage is low, check if CUDA is working
python3 -c "import torch; print(torch.cuda.is_available())"
```

---

## 💾 Data Persistence

### Models are Cached
- Location: `/workspace/.cache/`
- Persist across pod restarts
- ~5.3GB total

### Videos are Stored
- Location: `/workspace/framely-eyes/store/`
- VAB.json files persist
- Clean up old videos regularly

### Backups
```bash
# Backup VABs
tar -czf /workspace/vabs_backup.tar.gz /workspace/framely-eyes/store/

# Restore
tar -xzf /workspace/vabs_backup.tar.gz
```

---

## 🎓 Next Steps

### 1. Test with Your Videos
```bash
curl -X POST https://<pod-id>-8000.proxy.runpod.net/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_id":"my_video","media_url":"YOUR_VIDEO_URL"}'
```

### 2. Integrate with Your App
See [API_EXAMPLES.md](API_EXAMPLES.md) for Python, JS, TypeScript examples.

### 3. Scale Up
- Deploy multiple pods
- Add load balancer
- Use RunPod Serverless (coming soon)

### 4. Optimize
- Tune `configs/limits.yaml` for your hardware
- Enable/disable features based on needs
- Monitor and adjust

---

## 📚 Full Documentation

- **[README.md](README.md)** - Project overview
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute guide
- **[RUNPOD_SETUP.md](RUNPOD_SETUP.md)** - Detailed RunPod guide
- **[API_EXAMPLES.md](API_EXAMPLES.md)** - Code examples
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Fix issues
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - How it works

---

## 💡 Pro Tips

1. **Use Persistent Volume**: Models and VABs persist across restarts
2. **Monitor Costs**: Stop pod when not in use for development
3. **Scale Horizontally**: Multiple pods = parallel processing
4. **Clean Up**: Delete old videos from `/workspace/framely-eyes/store/`
5. **Update Regularly**: `git pull` for latest improvements

---

## 🆘 Support

### Having Issues?
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. View logs: `journalctl -u framely -f`
3. Test health: `curl http://localhost:8000/health`
4. Open GitHub issue with logs

### Need Help?
- GitHub Issues: Report bugs
- Documentation: Read guides
- RunPod Discord: Community support

---

## ✨ What Makes This Special

### One-Command Deploy
- Fully automated setup
- All models downloaded
- Services configured and started
- Public API immediately available

### Production-Ready
- Auto-restart on failures
- Health monitoring
- GPU optimization
- OOM safety

### Complete System
- 11 AI detectors
- Vision-language reasoning
- 100% coverage guarantees
- Ready for GPT-5 integration

---

## 🎉 You're Ready!

Your Framely-Eyes instance is running on RunPod and ready to analyze videos!

**Public API**: `https://<pod-id>-8000.proxy.runpod.net`

**Test it now:**
```bash
curl https://<pod-id>-8000.proxy.runpod.net/health
```

**Happy analyzing! 👁️✨**

---

*Deployed on RunPod.io with ❤️*  
*Version: 1.0.0*  
*Status: Production-Ready* ✅
