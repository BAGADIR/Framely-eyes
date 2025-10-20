# Production Deployment Guide

Complete guide for deploying Framely-Eyes in production environments.

---

## 🎯 Deployment Overview

### Architecture Tiers

**Tier 1: Single Node (Development/Small Scale)**
- 1 GPU server
- Docker Compose
- Local Redis
- ~10-50 videos/day

**Tier 2: Multi-Worker (Medium Scale)**
- 1 GPU server, multiple workers
- Shared Redis
- Load balancer
- ~100-500 videos/day

**Tier 3: Multi-Node (Enterprise Scale)**
- Multiple GPU servers
- Redis Cluster
- Kubernetes/Swarm
- ~1000+ videos/day

---

## 📋 Pre-Deployment Checklist

### Hardware Requirements
- [ ] NVIDIA GPU with 16GB+ VRAM
- [ ] 32GB+ system RAM
- [ ] 500GB+ SSD storage
- [ ] 1Gbps+ network
- [ ] CUDA 12.4+ drivers installed

### Software Requirements
- [ ] Linux (Ubuntu 22.04 recommended) or WSL2
- [ ] Docker Engine 24.0+
- [ ] Docker Compose 2.20+
- [ ] NVIDIA Container Toolkit
- [ ] nvidia-smi working

### Network Requirements
- [ ] Port 8000 available (API)
- [ ] Port 8001 available (Qwen)
- [ ] Port 6379 available (Redis)
- [ ] Outbound HTTPS for model downloads
- [ ] Firewall rules configured

---

## 🔧 Step 1: Server Preparation

### Install NVIDIA Drivers
```bash
# Check current driver
nvidia-smi

# If needed, install latest driver
sudo apt update
sudo apt install nvidia-driver-535
sudo reboot

# Verify
nvidia-smi
```

### Install Docker with GPU Support
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# Test
docker run --rm --gpus all nvidia/cuda:12.4.1-base nvidia-smi
```

---

## 🚀 Step 2: Application Deployment

### Clone Repository
```bash
cd /opt
sudo git clone <your-repo-url> framely-eyes
cd framely-eyes
sudo chown -R $USER:$USER .
```

### Configure Environment
```bash
# Copy example config
cp configs/settings.example.env configs/settings.env

# Edit configuration
nano configs/settings.env
```

**Production Settings:**
```bash
# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Storage
STORE_PATH=/mnt/storage/framely-eyes/store
MAX_VIDEO_MB=2000

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Security
MIME_WHITELIST=video/mp4,video/quicktime,video/x-matroska

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Tune Detection Parameters
```bash
nano configs/limits.yaml
```

**Production Tuning:**
```yaml
runtime:
  frame_stride: 1           # Keep at 1 for full coverage
  gpu_semaphore: 2          # Adjust based on VRAM
  qwen_context_max_frames: 12

detect:
  tile:
    size: 512              # Increase if GPU allows
    stride: 256
  superres:
    enabled: true          # Disable if speed priority
    trigger_min_h: 1440

audio:
  stoi:
    enabled: true          # Set false for non-speech content
```

### Download Model Weights
```bash
# Create model cache directory
mkdir -p ~/.cache/torch/hub/checkpoints/

# Download YOLO (automatic on first run)
python3 -c "from ultralytics import YOLO; YOLO('yolov8m.pt')"

# Download other models as needed
# (Most will auto-download on first use)
```

---

## 🐳 Step 3: Docker Configuration

### Production docker-compose.yml
```yaml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    image: framely/analyzer-api:1.0.0
    container_name: framely-api
    restart: unless-stopped
    env_file:
      - ./configs/settings.env
    volumes:
      - ./store:/app/store
      - model-cache:/app/.cache
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "8000:8000"
    deploy:
      resources:
        limits:
          memory: 16G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
    command: uvicorn services.api.api:app --host 0.0.0.0 --port 8000 --workers 1
    depends_on:
      - qwen
      - redis
    networks:
      - framely-net
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  qwen:
    image: vllm/vllm-openai:v0.5.0
    container_name: framely-qwen
    restart: unless-stopped
    command: >
      --model Qwen/Qwen2.5-VL-7B-Instruct
      --quantization awq
      --max-model-len 8192
      --gpu-memory-utilization 0.85
      --disable-log-requests
    deploy:
      resources:
        limits:
          memory: 24G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
    ports:
      - "127.0.0.1:8001:8000"
    volumes:
      - model-cache:/root/.cache
    networks:
      - framely-net
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    container_name: framely-redis
    restart: unless-stopped
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    networks:
      - framely-net
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 3s
      retries: 3

volumes:
  model-cache:
    driver: local
  redis-data:
    driver: local

networks:
  framely-net:
    driver: bridge
```

---

## 🔒 Step 4: Security Hardening

### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (if using nginx)
sudo ufw allow 443/tcp   # HTTPS (if using nginx)
sudo ufw enable

# Internal access only for services
# Redis and Qwen bound to 127.0.0.1
```

### Nginx Reverse Proxy (Optional but Recommended)
```bash
sudo apt install nginx

sudo nano /etc/nginx/sites-available/framely-eyes
```

**Nginx Config:**
```nginx
upstream framely_api {
    server localhost:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # File upload size
    client_max_body_size 2000M;

    # Timeouts for long-running requests
    proxy_read_timeout 600s;
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;

    location / {
        proxy_pass http://framely_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check endpoint (no auth)
    location /health {
        proxy_pass http://framely_api/health;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/framely-eyes /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### API Authentication (Add to router.py)
```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

security = HTTPBearer()
API_KEY = os.getenv("API_KEY", "your-secret-key")

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# Add to protected endpoints
@router.post("/analyze", dependencies=[Depends(verify_token)])
async def analyze_video(request: AnalyzeRequest):
    ...
```

---

## 📊 Step 5: Monitoring Setup

### Prometheus Metrics
Add to `docker-compose.yml`:
```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: framely-prometheus
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus-data:/prometheus
  ports:
    - "127.0.0.1:9090:9090"
  networks:
    - framely-net

grafana:
  image: grafana/grafana:latest
  container_name: framely-grafana
  ports:
    - "127.0.0.1:3000:3000"
  volumes:
    - grafana-data:/var/lib/grafana
  networks:
    - framely-net
```

**Prometheus Config** (`monitoring/prometheus.yml`):
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'framely-api'
    static_configs:
      - targets: ['api:8000']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### Log Aggregation
```bash
# Install Loki driver
docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions

# Update docker-compose.yml logging
logging:
  driver: loki
  options:
    loki-url: "http://localhost:3100/loki/api/v1/push"
```

---

## 🔄 Step 6: Backup Strategy

### Automated Backups
```bash
# Create backup script
sudo nano /usr/local/bin/framely-backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/mnt/backups/framely-eyes"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup VABs
rsync -av /opt/framely-eyes/store/ "$BACKUP_DIR/store_$DATE/"

# Backup Redis
docker exec framely-redis redis-cli --rdb /data/dump.rdb
cp /opt/framely-eyes/redis-data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Backup configs
tar -czf "$BACKUP_DIR/configs_$DATE.tar.gz" /opt/framely-eyes/configs/

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
sudo chmod +x /usr/local/bin/framely-backup.sh

# Add cron job (daily at 2 AM)
sudo crontab -e
0 2 * * * /usr/local/bin/framely-backup.sh >> /var/log/framely-backup.log 2>&1
```

---

## 🚦 Step 7: Health Checks & Monitoring

### Automated Health Checks
```bash
# Create health check script
nano /usr/local/bin/framely-health.sh
```

```bash
#!/bin/bash
API_URL="http://localhost:8000/health"
ALERT_EMAIL="ops@yourdomain.com"

response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ $response != "200" ]; then
    echo "Framely-Eyes health check failed! HTTP $response" | mail -s "ALERT: Framely-Eyes Down" $ALERT_EMAIL
    # Restart services
    cd /opt/framely-eyes
    docker compose restart
fi
```

```bash
chmod +x /usr/local/bin/framely-health.sh

# Run every 5 minutes
crontab -e
*/5 * * * * /usr/local/bin/framely-health.sh
```

### Uptime Monitoring
Use external service (UptimeRobot, Pingdom, etc.) to monitor:
- `https://your-domain.com/health`
- Alert on downtime
- Monitor response times

---

## 📈 Step 8: Performance Tuning

### GPU Optimization
```bash
# Set GPU persistence mode
nvidia-smi -pm 1

# Set maximum clock speeds
nvidia-smi -lgc 1800

# Monitor GPU
watch -n 1 nvidia-smi
```

### System Limits
```bash
# Increase file descriptors
sudo nano /etc/security/limits.conf
```

```
* soft nofile 65536
* hard nofile 65536
```

### Docker Resource Limits
Already set in docker-compose.yml, adjust as needed:
```yaml
deploy:
  resources:
    limits:
      memory: 16G      # Adjust based on available RAM
      cpus: '8'        # Adjust based on available CPUs
```

---

## 🔄 Step 9: Updates & Maintenance

### Update Procedure
```bash
# 1. Backup current state
/usr/local/bin/framely-backup.sh

# 2. Pull latest code
cd /opt/framely-eyes
git pull

# 3. Rebuild containers
docker compose build --no-cache

# 4. Stop services
docker compose down

# 5. Start with new version
docker compose up -d

# 6. Verify health
curl http://localhost:8000/health
```

### Rolling Updates (Zero Downtime)
```bash
# Scale up with new version
docker compose up -d --scale api=2 --no-recreate

# Wait for new instance to be healthy
sleep 30

# Remove old instance
docker compose up -d --scale api=1 --remove-orphans
```

---

## 📊 Step 10: Scaling

### Horizontal Scaling (Multiple Workers)
```yaml
# docker-compose.yml
services:
  api:
    # ... existing config ...
    deploy:
      replicas: 3  # Run 3 API instances
```

### Load Balancer (Nginx)
```nginx
upstream framely_api {
    least_conn;
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}
```

### Multi-Node (Kubernetes)
See `k8s/` directory for Kubernetes manifests (create if needed).

---

## 🧪 Step 11: Deployment Validation

### Post-Deployment Checklist
```bash
# 1. Health check
curl https://your-domain.com/health

# 2. Test analysis
curl -X POST https://your-domain.com/analyze \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "deploy_test",
    "media_url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"
  }'

# 3. Monitor logs
docker compose logs -f api

# 4. Check GPU usage
nvidia-smi

# 5. Verify Redis
docker exec framely-redis redis-cli ping

# 6. Test backup
/usr/local/bin/framely-backup.sh
```

---

## 🆘 Disaster Recovery

### Service Failure
```bash
# Restart individual service
docker compose restart api

# Restart all services
docker compose restart

# Full restart
docker compose down && docker compose up -d
```

### Data Corruption
```bash
# Restore from backup
cd /opt/framely-eyes
docker compose down
rm -rf store/* redis-data/*
rsync -av /mnt/backups/framely-eyes/store_LATEST/ store/
cp /mnt/backups/framely-eyes/redis_LATEST.rdb redis-data/dump.rdb
docker compose up -d
```

### Complete System Failure
1. Provision new server
2. Install dependencies (Step 1)
3. Restore from backups
4. Start services
5. Verify health

---

## 📝 Maintenance Schedule

### Daily
- ✅ Check logs for errors
- ✅ Monitor disk space
- ✅ Verify automated backups ran

### Weekly
- ✅ Review performance metrics
- ✅ Check GPU health
- ✅ Clean old videos from store/
- ✅ Update security patches

### Monthly
- ✅ Review and tune configuration
- ✅ Test disaster recovery
- ✅ Update dependencies
- ✅ Review access logs

---

## 🎯 Production Readiness Checklist

- [ ] Hardware meets requirements
- [ ] All dependencies installed
- [ ] Configuration files customized
- [ ] Model weights downloaded
- [ ] Docker containers running
- [ ] Health checks passing
- [ ] SSL/TLS configured
- [ ] Firewall rules set
- [ ] Monitoring enabled
- [ ] Backups automated
- [ ] Alerts configured
- [ ] Documentation updated
- [ ] Team trained
- [ ] Disaster recovery tested

---

**Deployment Status**: Ready for Production 🚀

Follow this guide step-by-step for a successful deployment!
