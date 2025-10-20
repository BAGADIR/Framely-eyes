# 🚀 Getting Started with Framely-Eyes

**The fastest path from zero to analyzing videos in production.**

---

## 🎯 Quick Navigation

**Just want to test it?** → Follow **Path 1: Quick Test** (5 minutes)  
**Ready for production?** → Follow **Path 2: Production Deploy** (30 minutes)  
**Want to understand it?** → Follow **Path 3: Deep Dive** (2 hours)

---

## 🛤️ Path 1: Quick Test (5 Minutes)

### Prerequisites
- NVIDIA GPU with CUDA
- Docker with GPU support
- 16GB+ VRAM

### Steps

**1. Start Services**
```bash
cd Framely-eyes
docker compose -f docker/docker-compose.yml up -d
```

**2. Wait for Services (2-3 min)**
```bash
# Check status
docker compose -f docker/docker-compose.yml ps

# Wait until all 3 services are "Up"
```

**3. Test Health**
```bash
curl http://localhost:8000/health
```

Expected: `"status": "healthy"`

**4. Analyze Test Video**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test_001",
    "media_url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
  }'
```

**5. Check Results**
```bash
# Wait 2-3 minutes, then:
curl http://localhost:8000/result/test_001 > result.json

# View
cat result.json | jq '.status.state'  # Should show "ok"
cat result.json | jq '.shots[0].summary'  # Shot summary
```

**✅ Success!** You've analyzed your first video.

**Next:** Try your own video or read QUICKSTART.md

---

## 🏭 Path 2: Production Deploy (30 Minutes)

### Phase 1: Prepare (10 min)

**1. Check Prerequisites**
```bash
# GPU available?
nvidia-smi

# Docker ready?
docker run --rm --gpus all nvidia/cuda:12.4.1-base nvidia-smi
```

**2. Configure**
```bash
# Copy config template
cp configs/settings.example.env configs/settings.env

# Edit settings (use nano or your editor)
nano configs/settings.env
```

Change these for production:
```bash
MAX_VIDEO_MB=2000
LOG_LEVEL=INFO
STORE_PATH=/mnt/storage/framely-eyes/store
```

**3. Tune Detection**
```bash
nano configs/limits.yaml
```

Adjust `gpu_semaphore` based on your VRAM:
- 16GB VRAM → `gpu_semaphore: 1`
- 24GB VRAM → `gpu_semaphore: 2`
- 48GB VRAM → `gpu_semaphore: 3`

### Phase 2: Deploy (10 min)

**1. Build**
```bash
docker compose -f docker/docker-compose.yml build
```

**2. Start**
```bash
docker compose -f docker/docker-compose.yml up -d
```

**3. Verify**
```bash
# Health check
curl http://localhost:8000/health

# Run smoke test
bash scripts/smoke_test.sh
```

### Phase 3: Secure (10 min)

**1. Setup Firewall**
```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

**2. Setup Backups**
```bash
# Create backup script (see DEPLOYMENT_GUIDE.md)
sudo cp deployment/backup.sh /usr/local/bin/framely-backup.sh
sudo chmod +x /usr/local/bin/framely-backup.sh

# Schedule daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/framely-backup.sh") | crontab -
```

**3. Setup Monitoring**
```bash
# Add health check cron
(crontab -l 2>/dev/null; echo "*/5 * * * * curl -f http://localhost:8000/health || systemctl restart docker") | crontab -
```

**✅ Production Ready!**

**Next:** Read DEPLOYMENT_GUIDE.md for advanced setup

---

## 📚 Path 3: Deep Dive (2 Hours)

### Hour 1: Understanding

**1. Read Core Docs (40 min)**
- [README.md](README.md) - Overview (10 min)
- [ARCHITECTURE.md](ARCHITECTURE.md) - Design (15 min)
- [API_EXAMPLES.md](API_EXAMPLES.md) - Integration (15 min)

**2. Explore Code (20 min)**
- `services/orchestrator/orchestrator.py` - Main engine
- `services/detectors/yolo.py` - Example detector
- `services/api/router.py` - API endpoints

### Hour 2: Hands-On

**1. Process Multiple Videos (20 min)**
```bash
# Upload 3 videos
for i in {1..3}; do
  curl -X POST http://localhost:8000/analyze \
    -H "Content-Type: application/json" \
    -d "{\"video_id\":\"video_$i\",\"media_url\":\"YOUR_VIDEO_URL\"}"
done

# Monitor progress
watch -n 5 'curl -s http://localhost:8000/status/video_1'
```

**2. Analyze Results (20 min)**
```bash
# Get VAB
curl http://localhost:8000/result/video_1 > vab.json

# Explore structure
cat vab.json | jq '.status.coverage'
cat vab.json | jq '.shots[0].detectors.objects'
cat vab.json | jq '.shots[0].detectors.audio'
cat vab.json | jq '.risks'
```

**3. Customize (20 min)**
```bash
# Try different configurations
nano configs/limits.yaml

# Restart to apply
docker compose restart

# Test with ablations
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test_ablation",
    "media_url": "...",
    "ablations": {"no_sr": true, "light_audio": true}
  }'
```

**✅ Expert Level!**

**Next:** Read CONTRIBUTING.md to add features

---

## 🗺️ Documentation Map

### 🟢 Start Here
- **[README.md](README.md)** - Project overview
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute guide
- **This file** - Getting started paths

### 🔵 Integration
- **[API_EXAMPLES.md](API_EXAMPLES.md)** - Code samples
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design

### 🟡 Operations
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production setup
- **[LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md)** - Pre-launch verification
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Problem solving

### 🟠 Development
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Add features
- **[FILE_INDEX.md](FILE_INDEX.md)** - Complete file listing

### 🟣 Project Info
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Executive overview
- **[PROJECT_COMPLETION.md](PROJECT_COMPLETION.md)** - Completion certificate
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

---

## 💡 Common Tasks

### Test with Your Own Video
```bash
# Option 1: URL
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_id":"my_video","media_url":"https://your-url.com/video.mp4"}'

# Option 2: Upload
curl -X POST http://localhost:8000/ingest \
  -F "video_id=my_video" \
  -F "file=@/path/to/video.mp4"

curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_id":"my_video"}'
```

### Monitor Progress
```bash
# Real-time status
watch -n 2 'curl -s http://localhost:8000/status/my_video | jq .'

# Or check logs
docker compose -f docker/docker-compose.yml logs -f api
```

### View Results
```bash
# Get full VAB
curl http://localhost:8000/result/my_video > my_vab.json

# Pretty print
cat my_vab.json | jq '.'

# Extract specific data
cat my_vab.json | jq '.status.coverage'
cat my_vab.json | jq '.shots[] | {id: .shot_id, summary: .summary}'
```

### Stop Services
```bash
docker compose -f docker/docker-compose.yml down
```

### Check Logs
```bash
# All services
docker compose -f docker/docker-compose.yml logs

# Specific service
docker compose -f docker/docker-compose.yml logs api
docker compose -f docker/docker-compose.yml logs qwen
docker compose -f docker/docker-compose.yml logs redis
```

### Update Configuration
```bash
# Edit config
nano configs/limits.yaml

# Restart to apply
docker compose -f docker/docker-compose.yml restart
```

---

## 🚨 Quick Troubleshooting

### Service Won't Start
```bash
# Check logs
docker compose logs api

# Check GPU
nvidia-smi

# Restart
docker compose restart
```

### Analysis Fails
```bash
# Check status
curl http://localhost:8000/status/video_id

# Check logs
docker compose logs api | grep ERROR

# Try with ablations (less memory)
curl -X POST http://localhost:8000/analyze \
  -d '{"video_id":"test","media_url":"...","ablations":{"no_sr":true}}'
```

### Out of Memory
```bash
# Edit config
nano configs/limits.yaml

# Reduce gpu_semaphore from 2 to 1
# Or enable ablations
```

**More help:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 🎓 Learning Resources

### Video Tutorials
1. Watch demo video (if available)
2. Follow QUICKSTART.md
3. Read API examples

### Code Examples
- **Python:** [API_EXAMPLES.md](API_EXAMPLES.md#7-python-client-example)
- **JavaScript:** [API_EXAMPLES.md](API_EXAMPLES.md#8-javascripttypescript-client-example)
- **cURL:** [API_EXAMPLES.md](API_EXAMPLES.md)

### Sample Videos
- Test Videos: https://test-videos.co.uk/
- Free Stock: https://pixabay.com/videos/

---

## 🎯 Next Steps by Role

### **Video Editor / Content Creator**
1. Start with **Path 1** (Quick Test)
2. Process your videos
3. Integrate VAB with your editing workflow
4. Provide feedback on detection quality

### **Developer / Integrator**
1. Follow **Path 1** (Quick Test)
2. Read [API_EXAMPLES.md](API_EXAMPLES.md)
3. Build client integration
4. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand system

### **DevOps / SRE**
1. Follow **Path 2** (Production Deploy)
2. Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. Complete [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md)
4. Setup monitoring & backups

### **Data Scientist / ML Engineer**
1. Follow **Path 3** (Deep Dive)
2. Read [CONTRIBUTING.md](CONTRIBUTING.md)
3. Add custom detectors
4. Tune for your use case

---

## 🆘 Getting Help

### Self-Service
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review logs: `docker compose logs`
3. Test health: `curl http://localhost:8000/health`

### Documentation
- Search in README.md
- Check API_EXAMPLES.md
- Review ARCHITECTURE.md

### Community
- Open GitHub issue
- Check existing issues
- Contribute improvements

---

## ✨ Success Stories

### What You Can Build

**AI Video Editor**
```python
# Get VAB
vab = analyze_video("my_video.mp4")

# Feed to GPT-5
prompt = f"Based on this analysis: {vab}, create an engaging 30-second edit"
edit_instructions = gpt5.generate(prompt)

# Apply edits automatically
```

**Content Moderator**
```python
# Check for risks
if vab["risks"]:
    for risk in vab["risks"]:
        if risk["severity"] == "high":
            flag_for_review(video_id)
```

**Video Search Engine**
```python
# Index by content
for shot in vab["shots"]:
    index.add({
        "video_id": video_id,
        "shot_id": shot["shot_id"],
        "objects": shot["detectors"]["objects"],
        "text": shot["detectors"]["text"],
        "mood": shot["mood"]
    })

# Search: "videos with cats"
results = index.search("cat", field="objects.label")
```

---

## 🎉 You're Ready!

**Choose your path above and start analyzing videos like never before.**

**Questions?** Check the docs.  
**Issues?** See troubleshooting.  
**Ideas?** Start contributing.

**Welcome to the future of video understanding! 👁️✨**

---

*Last updated: October 20, 2025*  
*Version: 1.0.0*
