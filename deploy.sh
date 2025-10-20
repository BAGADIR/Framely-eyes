#!/bin/bash
# ONE-COMMAND DEPLOYMENT FOR RUNPOD
# Run this on your RunPod instance after SSH

set -e

echo "╔══════════════════════════════════════════╗"
echo "║   FRAMELY-EYES DEPLOYMENT                ║"
echo "║   RunPod Instance: 38tdck85q5uma9        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check we're on RunPod
echo -e "${YELLOW}[1/6]${NC} Checking environment..."
if [ ! -d "/workspace" ]; then
    echo -e "${RED}ERROR: /workspace not found. Are you on RunPod?${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} RunPod detected"

# Step 2: Check GPU
echo ""
echo -e "${YELLOW}[2/6]${NC} Checking GPU..."
if ! nvidia-smi > /dev/null 2>&1; then
    echo -e "${RED}ERROR: nvidia-smi not found. No GPU?${NC}"
    exit 1
fi
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
echo -e "${GREEN}✓${NC} GPU: $GPU_NAME ($GPU_MEM)"

# Step 3: Clone/Update repo
echo ""
echo -e "${YELLOW}[3/6]${NC} Setting up code..."
cd /workspace
if [ -d "framely-eyes" ]; then
    echo "Repository exists, updating..."
    cd framely-eyes
    git pull
else
    echo "Cloning repository..."
    if [ -z "$1" ]; then
        echo -e "${RED}ERROR: Please provide repository URL${NC}"
        echo "Usage: ./deploy.sh https://github.com/YOUR_USERNAME/framely-eyes.git"
        exit 1
    fi
    git clone "$1" framely-eyes
    cd framely-eyes
fi
echo -e "${GREEN}✓${NC} Code ready at /workspace/framely-eyes"

# Step 4: Build Docker image
echo ""
echo -e "${YELLOW}[4/6]${NC} Building Docker image..."
echo "This will take 10-15 minutes (one time only)..."
docker build -f docker/Dockerfile.runpod -t framely:latest . || {
    echo -e "${RED}ERROR: Docker build failed${NC}"
    exit 1
}
echo -e "${GREEN}✓${NC} Docker image built"

# Step 5: Stop old container if exists
echo ""
echo -e "${YELLOW}[5/6]${NC} Preparing to start..."
if docker ps -a | grep -q framely; then
    echo "Removing old container..."
    docker rm -f framely || true
fi

# Step 6: Start container
echo ""
echo -e "${YELLOW}[6/6]${NC} Starting Framely-Eyes..."
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

echo ""
echo "Waiting for services to start (this takes 10-15 min on first run)..."
echo "Models are downloading in background..."
echo ""
echo "To follow logs:"
echo -e "${GREEN}docker logs -f framely${NC}"
echo ""

# Wait a bit then check status
sleep 5

if docker ps | grep -q framely; then
    echo -e "${GREEN}✓ Container running!${NC}"
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║          DEPLOYMENT SUCCESSFUL           ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""
    echo "📊 Service Info:"
    echo "  Local URL:  http://localhost:8000"
    echo "  Public URL: https://38tdck85q5uma9-8000.proxy.runpod.net"
    echo ""
    echo "🔍 Check Status:"
    echo "  docker logs -f framely"
    echo ""
    echo "🧪 Test When Ready (after 10-15 min):"
    echo '  curl http://localhost:8000/health'
    echo ""
    echo "⏰ First-time setup is downloading models (~5GB)"
    echo "   This happens in background. Check logs to monitor."
    echo ""
else
    echo -e "${RED}ERROR: Container failed to start${NC}"
    echo "Check logs: docker logs framely"
    exit 1
fi
