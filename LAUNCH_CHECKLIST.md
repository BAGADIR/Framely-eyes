# 🚀 Framely-Eyes Launch Checklist

**Complete pre-launch verification for production deployment**

---

## ✅ Phase 1: Infrastructure Verification

### Hardware ✓
- [ ] NVIDIA GPU detected: `nvidia-smi`
- [ ] VRAM ≥ 16GB: `nvidia-smi | grep "MiB"`
- [ ] System RAM ≥ 32GB: `free -h`
- [ ] Disk space ≥ 500GB: `df -h`
- [ ] CUDA 12.4+ installed: `nvcc --version`
- [ ] GPU temperature normal (<80°C): `nvidia-smi`

### Software Dependencies ✓
- [ ] Docker installed: `docker --version`
- [ ] Docker Compose installed: `docker compose version`
- [ ] NVIDIA Container Toolkit: `docker run --rm --gpus all nvidia/cuda:12.4.1-base nvidia-smi`
- [ ] Git installed: `git --version`
- [ ] Python 3.10+ available: `python3 --version`

### Network ✓
- [ ] Port 8000 free: `netstat -tuln | grep 8000`
- [ ] Port 8001 free: `netstat -tuln | grep 8001`
- [ ] Port 6379 free: `netstat -tuln | grep 6379`
- [ ] Outbound HTTPS working: `curl https://huggingface.co`
- [ ] DNS resolution: `ping google.com`

---

## ✅ Phase 2: Application Setup

### Repository ✓
- [ ] Code cloned: `ls /opt/framely-eyes`
- [ ] Correct branch: `git branch`
- [ ] Latest version: `git pull`
- [ ] Permissions set: `ls -la /opt/framely-eyes`

### Configuration ✓
- [ ] `settings.env` created: `ls configs/settings.env`
- [ ] API_PORT configured
- [ ] STORE_PATH configured
- [ ] MAX_VIDEO_MB set
- [ ] LOG_LEVEL set (INFO for prod)
- [ ] MIME_WHITELIST verified
- [ ] `limits.yaml` tuned for hardware
- [ ] `model_paths.yaml` reviewed

### Model Weights ✓
- [ ] YOLO weights available: `python3 -c "from ultralytics import YOLO; YOLO('yolov8m.pt')"`
- [ ] Model cache directory created: `mkdir -p ~/.cache/torch`
- [ ] Sufficient disk space for models (10GB+)

---

## ✅ Phase 3: Docker Deployment

### Build ✓
- [ ] Docker daemon running: `systemctl status docker`
- [ ] Images built: `docker compose -f docker/docker-compose.yml build`
- [ ] No build errors in logs
- [ ] Images listed: `docker images | grep framely`

### Container Start ✓
- [ ] Services started: `docker compose -f docker/docker-compose.yml up -d`
- [ ] All containers running: `docker compose ps`
- [ ] API container healthy: `docker inspect framely-api | grep Status`
- [ ] Qwen container healthy: `docker inspect framely-qwen | grep Status`
- [ ] Redis container healthy: `docker inspect framely-redis | grep Status`

### Container Logs ✓
- [ ] No errors in API logs: `docker compose logs api | grep ERROR`
- [ ] No errors in Qwen logs: `docker compose logs qwen | grep ERROR`
- [ ] No errors in Redis logs: `docker compose logs redis | grep ERROR`
- [ ] GPU detected in logs: `docker compose logs api | grep CUDA`

---

## ✅ Phase 4: Service Health Checks

### API Health ✓
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

- [ ] status = "healthy"
- [ ] gpu_available = true
- [ ] redis_connected = true
- [ ] qwen_available = true
- [ ] Response time < 1 second

### Component Health ✓
- [ ] **GPU**: `nvidia-smi` shows processes
- [ ] **Redis**: `docker exec framely-redis redis-cli ping` returns "PONG"
- [ ] **Qwen**: `curl http://localhost:8001/health` returns 200
- [ ] **Disk**: `df -h | grep /opt/framely-eyes` shows space available

---

## ✅ Phase 5: Functional Testing

### Smoke Test ✓
```bash
bash scripts/smoke_test.sh
```

Expected:
- [ ] ✓ Health check passes
- [ ] ✓ Job queued successfully
- [ ] ✓ Job completes (within 5 min)
- [ ] ✓ VAB has schema_version
- [ ] ✓ VAB has status
- [ ] ✓ VAB has scenes
- [ ] ✓ VAB has shots
- [ ] ✓ Coverage ≥ 99%

### Manual API Test ✓
```bash
# 1. Upload test video
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "launch_test",
    "media_url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
  }'

# 2. Check status
curl http://localhost:8000/status/launch_test

# 3. Get results
curl http://localhost:8000/result/launch_test > launch_vab.json

# 4. Validate VAB
cat launch_vab.json | jq '.status.state'  # Should be "ok"
```

- [ ] Job submitted successfully
- [ ] Status updates properly
- [ ] VAB generated correctly
- [ ] Coverage metrics present
- [ ] Provenance tracking present
- [ ] No risks detected (for test video)

### Detector Validation ✓
```bash
cat launch_vab.json | jq '.shots[0].detectors | keys'
```

Expected detectors:
- [ ] objects
- [ ] faces
- [ ] text
- [ ] color
- [ ] motion
- [ ] audio
- [ ] transition

### Performance Baseline ✓
- [ ] Analysis completed in < 5 minutes for 10s video
- [ ] GPU utilization reached 80-100% during analysis
- [ ] Memory usage stayed within limits
- [ ] No OOM errors
- [ ] VRAM peak < available VRAM

---

## ✅ Phase 6: Security Hardening

### Access Control ✓
- [ ] Firewall rules configured: `sudo ufw status`
- [ ] Only necessary ports open
- [ ] Redis not exposed externally: `netstat -tuln | grep 6379`
- [ ] Qwen not exposed externally: `netstat -tuln | grep 8001`
- [ ] SSH key-based auth enabled
- [ ] Root login disabled

### API Security ✓
- [ ] API key authentication implemented (if needed)
- [ ] HTTPS configured (if public)
- [ ] CORS settings appropriate
- [ ] File upload limits enforced
- [ ] MIME type validation working
- [ ] Request size limits configured

### Data Security ✓
- [ ] Store directory permissions: `ls -la store/`
- [ ] Config files protected: `chmod 600 configs/settings.env`
- [ ] Logs rotation configured
- [ ] Sensitive data not in logs
- [ ] Backup encryption enabled (if applicable)

---

## ✅ Phase 7: Monitoring & Logging

### Logging ✓
- [ ] Logs writing to correct location
- [ ] Log rotation configured: `ls /var/log/framely-*`
- [ ] Log level appropriate (INFO for prod)
- [ ] JSON logging enabled (if required)
- [ ] Centralized logging (if applicable)

### Metrics ✓
- [ ] Prometheus scraping (if configured)
- [ ] Grafana dashboards (if configured)
- [ ] GPU metrics visible
- [ ] API metrics visible
- [ ] Redis metrics visible

### Alerting ✓
- [ ] Health check alerts configured
- [ ] Disk space alerts configured
- [ ] GPU temperature alerts configured
- [ ] Error rate alerts configured
- [ ] Email/Slack notifications tested

---

## ✅ Phase 8: Backup & Recovery

### Backup Setup ✓
- [ ] Backup script created: `ls /usr/local/bin/framely-backup.sh`
- [ ] Backup script executable: `chmod +x /usr/local/bin/framely-backup.sh`
- [ ] Backup destination configured
- [ ] Backup cron job added: `crontab -l`
- [ ] First backup completed: `/usr/local/bin/framely-backup.sh`
- [ ] Backup verified: `ls -la /mnt/backups/framely-eyes/`

### Recovery Testing ✓
- [ ] Restore procedure documented
- [ ] Test restore performed
- [ ] Recovery time measured (RTO)
- [ ] Data integrity verified (RPO)

---

## ✅ Phase 9: Performance Optimization

### Configuration Tuning ✓
- [ ] `gpu_semaphore` optimized for hardware
- [ ] `frame_stride` set appropriately
- [ ] `qwen_context_max_frames` tuned
- [ ] Tile size/stride optimized
- [ ] Super-resolution enabled/disabled as needed
- [ ] Audio analysis tuned

### System Tuning ✓
- [ ] GPU persistence mode: `nvidia-smi -pm 1`
- [ ] GPU clocks maximized: `nvidia-smi -lgc 1800`
- [ ] File descriptor limits increased
- [ ] Docker resource limits appropriate
- [ ] Swap configured (if needed)

### Load Testing ✓
- [ ] Single video analysis successful
- [ ] Multiple videos processed sequentially
- [ ] System stability under load
- [ ] Memory leaks checked
- [ ] Performance degradation measured

---

## ✅ Phase 10: Documentation & Training

### Documentation ✓
- [ ] README.md updated
- [ ] QUICKSTART.md verified
- [ ] API_EXAMPLES.md tested
- [ ] TROUBLESHOOTING.md complete
- [ ] DEPLOYMENT_GUIDE.md followed
- [ ] Internal runbooks created

### Team Preparation ✓
- [ ] Operations team trained
- [ ] Development team briefed
- [ ] Support team informed
- [ ] Escalation procedures defined
- [ ] Contact list updated

---

## ✅ Phase 11: Production Readiness

### Final Verification ✓
```bash
# Run comprehensive check
./scripts/production_readiness_check.sh
```

- [ ] All services healthy
- [ ] Test video processed successfully
- [ ] Coverage guarantees met
- [ ] Performance within SLA
- [ ] No critical errors in logs
- [ ] Monitoring dashboards green
- [ ] Backups running
- [ ] Alerts functioning

### Go/No-Go Criteria ✓
- [ ] **Critical**: All Phase 1-5 items complete
- [ ] **Critical**: Smoke test passes
- [ ] **Critical**: Security hardened
- [ ] **Important**: Monitoring configured
- [ ] **Important**: Backups automated
- [ ] **Nice-to-have**: Load testing complete

---

## ✅ Phase 12: Launch

### Pre-Launch ✓
- [ ] Announce maintenance window (if applicable)
- [ ] Stakeholders notified
- [ ] Support team on standby
- [ ] Rollback plan ready
- [ ] Communication channels open

### Launch Sequence ✓
1. [ ] Final backup: `/usr/local/bin/framely-backup.sh`
2. [ ] Start services: `docker compose up -d`
3. [ ] Verify health: `curl http://localhost:8000/health`
4. [ ] Process test video
5. [ ] Monitor for 15 minutes
6. [ ] Enable external access (if applicable)
7. [ ] Announce launch

### Post-Launch Monitoring ✓
- [ ] **Hour 1**: Check every 5 minutes
- [ ] **Hour 2-4**: Check every 15 minutes
- [ ] **Hour 4-24**: Check every hour
- [ ] **Day 2-7**: Check twice daily

---

## 📊 Launch Metrics Baseline

### Performance Targets
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| API response time | < 100ms | ___ | ⬜ |
| Video analysis time | ~1-2 min/min | ___ | ⬜ |
| GPU utilization | 80-100% | ___ | ⬜ |
| Memory usage | < 80% | ___ | ⬜ |
| Uptime | 99.9% | ___ | ⬜ |
| Coverage | ≥ 99% | ___ | ⬜ |

### Quality Targets
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Object detection TPR | 94% | ___ | ⬜ |
| OCR accuracy | 97% | ___ | ⬜ |
| Audio coverage | 100% | ___ | ⬜ |
| Temporal coverage | 100% | ___ | ⬜ |
| Spatial coverage | 100% | ___ | ⬜ |

---

## 🆘 Emergency Contacts

### Technical
- **On-Call Engineer**: _________________
- **DevOps Lead**: _________________
- **System Admin**: _________________

### Business
- **Product Owner**: _________________
- **Project Manager**: _________________
- **Executive Sponsor**: _________________

---

## 📝 Sign-Off

### Technical Approval
- [ ] **Lead Engineer**: _________________ Date: _______
- [ ] **DevOps Lead**: _________________ Date: _______
- [ ] **QA Lead**: _________________ Date: _______

### Business Approval
- [ ] **Product Owner**: _________________ Date: _______
- [ ] **Operations Manager**: _________________ Date: _______

---

## 🎉 LAUNCH STATUS

**Status**: ⬜ NOT LAUNCHED | ⬜ IN PROGRESS | ⬜ LAUNCHED

**Launch Date**: _________________

**Launch Time**: _________________

**Launched By**: _________________

---

## 📋 Post-Launch Review (Day 7)

### Metrics Review
- [ ] Performance targets met
- [ ] Quality targets met
- [ ] No critical incidents
- [ ] User feedback positive
- [ ] System stable

### Lessons Learned
- What went well: _________________
- What needs improvement: _________________
- Action items: _________________

---

## ✨ Congratulations!

**Framely-Eyes is LIVE! 🚀👁️**

Your GPU-first Video Perception OS is now analyzing videos in production.

**Next Steps:**
1. Monitor closely for first 24 hours
2. Gather user feedback
3. Optimize based on real workloads
4. Plan for scale

**Remember:**
- Check logs daily
- Monitor metrics
- Keep backups current
- Update documentation
- Celebrate wins! 🎊

---

*This checklist should be completed before every production deployment.*
