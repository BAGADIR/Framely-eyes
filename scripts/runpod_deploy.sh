#!/bin/bash
# Automated RunPod deployment script for Framely-Eyes

set -e

echo "========================================"
echo "🚀 Framely-Eyes RunPod Deployment"
echo "========================================"
echo ""

# Check if running on RunPod
if [ ! -d "/workspace" ]; then
    echo "⚠️  Warning: Not running on RunPod (/workspace not found)"
    echo "This script is optimized for RunPod.io"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: System Setup
echo "📦 Step 1/7: Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq \
    ffmpeg \
    redis-server \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    > /dev/null 2>&1
echo "✅ System dependencies installed"

# Step 2: Clone or Update Repository
echo ""
echo "📥 Step 2/7: Setting up repository..."
cd /workspace

if [ -d "framely-eyes" ]; then
    echo "Repository exists, updating..."
    cd framely-eyes
    git pull
else
    echo "Cloning repository..."
    read -p "Enter repository URL: " REPO_URL
    git clone $REPO_URL framely-eyes
    cd framely-eyes
fi
echo "✅ Repository ready"

# Step 3: Install Python Dependencies
echo ""
echo "🐍 Step 3/7: Installing Python packages..."
echo "This will take 5-10 minutes..."
pip install -q --upgrade pip setuptools wheel
pip install -q -r requirements.txt
pip install -q -r requirements-models.txt
echo "✅ Python packages installed"

# Step 4: Initialize Models
echo ""
echo "📦 Step 4/7: Downloading AI models..."
echo "This will take 10-15 minutes (one-time only)..."
python3 << 'PYTHON'
from services.utils.model_manager import initialize_models
import logging
logging.basicConfig(level=logging.INFO)
results = initialize_models()
failed = [k for k, v in results.items() if not v]
if failed:
    print(f'\n⚠️  Some models unavailable: {failed}')
    print('System will continue with available models\n')
PYTHON
echo "✅ Models initialized"

# Step 5: Configure
echo ""
echo "⚙️  Step 5/7: Configuring application..."
if [ ! -f "configs/settings.env" ]; then
    cp configs/settings.example.env configs/settings.env
    
    # Set RunPod-specific paths
    sed -i 's|STORE_PATH=.*|STORE_PATH=/workspace/framely-eyes/store|' configs/settings.env
    sed -i 's|MODEL_CACHE=.*|MODEL_CACHE=/workspace/.cache|' configs/settings.env
    sed -i 's|REDIS_HOST=.*|REDIS_HOST=127.0.0.1|' configs/settings.env
    
    echo "✅ Configuration created"
else
    echo "✅ Configuration already exists"
fi

# Create necessary directories
mkdir -p /workspace/.cache /workspace/framely-eyes/store
ln -sf /workspace/.cache ~/.cache 2>/dev/null || true

# Step 6: Start Services
echo ""
echo "🚀 Step 6/7: Starting services..."

# Start Redis
if ! pgrep redis-server > /dev/null; then
    redis-server --daemonize yes --bind 127.0.0.1
    sleep 2
    echo "✅ Redis started"
else
    echo "✅ Redis already running"
fi

# Check if we should start Qwen locally
echo ""
read -p "Start Qwen-VL locally? (requires 8GB+ VRAM) (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting Qwen-VL (this will take 2-3 minutes)..."
    
    # Check if vLLM is installed
    if ! python3 -c "import vllm" 2>/dev/null; then
        echo "Installing vLLM..."
        pip install -q vllm
    fi
    
    # Start Qwen in background
    nohup python3 -m vllm.entrypoints.openai.api_server \
        --model Qwen/Qwen2.5-VL-7B-Instruct \
        --quantization awq \
        --max-model-len 8192 \
        --gpu-memory-utilization 0.5 \
        --port 8001 \
        --host 0.0.0.0 \
        > /workspace/qwen.log 2>&1 &
    
    QWEN_PID=$!
    echo "Qwen-VL started with PID: $QWEN_PID"
    echo "Waiting for Qwen to load..."
    sleep 60
    
    # Verify Qwen is responding
    if curl -s http://localhost:8001/health > /dev/null; then
        echo "✅ Qwen-VL ready"
    else
        echo "⚠️  Qwen-VL may still be loading, check logs: tail -f /workspace/qwen.log"
    fi
else
    echo "⚠️  Skipping Qwen-VL (use external service)"
    echo "Set QWEN_API_BASE in configs/settings.env to external Qwen service"
fi

# Step 7: Start API
echo ""
echo "🌐 Step 7/7: Starting Framely-Eyes API..."
echo ""

# Create systemd service for auto-restart
cat > /etc/systemd/system/framely.service <<'EOF'
[Unit]
Description=Framely-Eyes API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace/framely-eyes
Environment="PYTHONPATH=/workspace/framely-eyes"
ExecStart=/usr/local/bin/uvicorn services.api.api:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable framely
systemctl start framely

sleep 3

# Verify API is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API started successfully"
else
    echo "⚠️  API may still be starting..."
fi

# Get public URL
echo ""
echo "========================================"
echo "✅ Deployment Complete!"
echo "========================================"
echo ""
echo "📊 Service Status:"
systemctl status framely --no-pager | head -5

echo ""
echo "🌐 Access Your API:"
if [ -n "$RUNPOD_POD_ID" ]; then
    echo "  Public URL: https://${RUNPOD_POD_ID}-8000.proxy.runpod.net"
else
    echo "  Local: http://localhost:8000"
    echo "  RunPod Proxy: https://<pod-id>-8000.proxy.runpod.net"
fi

echo ""
echo "📖 Quick Test:"
echo "  curl http://localhost:8000/health"
echo ""
echo "📝 View Logs:"
echo "  journalctl -u framely -f"
echo ""
echo "🔄 Restart Service:"
echo "  systemctl restart framely"
echo ""
echo "📚 Full Documentation:"
echo "  cat /workspace/framely-eyes/RUNPOD_SETUP.md"
echo ""
echo "========================================"
echo "🎉 Happy Analyzing!"
echo "========================================"
