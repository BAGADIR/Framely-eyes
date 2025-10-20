#!/bin/bash
# COMPLETE INSTALLATION SCRIPT FOR RUNPOD
# This installs EVERYTHING - no compromises

set -e  # Exit on any error

echo "════════════════════════════════════════════════════════"
echo "  FRAMELY-EYES COMPLETE INSTALLATION"
echo "════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: System Dependencies
echo -e "${YELLOW}[1/7]${NC} Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq \
    ffmpeg \
    redis-server \
    libsndfile1 \
    libgl1 \
    libglib2.0-0t64 \
    git \
    curl \
    wget \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    > /dev/null 2>&1

echo -e "${GREEN}✓${NC} System dependencies installed"

# Step 2: Upgrade pip
echo ""
echo -e "${YELLOW}[2/7]${NC} Upgrading pip..."
pip install --upgrade pip setuptools wheel -q
echo -e "${GREEN}✓${NC} Pip upgraded"

# Step 3: Install PyTorch (if not already installed)
echo ""
echo -e "${YELLOW}[3/7]${NC} Checking PyTorch..."
if python3 -c "import torch" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} PyTorch already installed"
else
    echo "Installing PyTorch with CUDA..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
fi

# Step 4: Install SAM2 from source
echo ""
echo -e "${YELLOW}[4/7]${NC} Installing SAM2 from GitHub..."
pip install git+https://github.com/facebookresearch/segment-anything-2.git -q
echo -e "${GREEN}✓${NC} SAM2 installed"

# Step 5: Install core requirements
echo ""
echo -e "${YELLOW}[5/7]${NC} Installing core Python packages..."
echo "This will take 5-10 minutes..."
pip install -r requirements.txt -q
echo -e "${GREEN}✓${NC} Core packages installed"

# Step 6: Install model-specific requirements
echo ""
echo -e "${YELLOW}[6/7]${NC} Installing model packages..."
pip install -r requirements-models.txt -q
echo -e "${GREEN}✓${NC} Model packages installed"

# Step 7: Pre-download models
echo ""
echo -e "${YELLOW}[7/7]${NC} Pre-downloading AI models..."
echo "This will download ~5GB of models..."

# Create cache directory
mkdir -p /workspace/.cache

# Download YOLO
python3 << 'EOF'
import sys
try:
    from ultralytics import YOLO
    print("Downloading YOLOv8m...")
    model = YOLO('yolov8m.pt')
    print("✓ YOLO downloaded")
except Exception as e:
    print(f"⚠ YOLO download failed (will auto-download on first use): {e}")
EOF

# Download InsightFace
python3 << 'EOF'
import sys
try:
    import insightface
    from insightface.app import FaceAnalysis
    print("Downloading InsightFace models...")
    app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    print("✓ InsightFace downloaded")
except Exception as e:
    print(f"⚠ InsightFace download failed (will auto-download on first use): {e}")
EOF

# Download PaddleOCR
python3 << 'EOF'
import sys
try:
    from paddleocr import PaddleOCR
    print("Downloading PaddleOCR models...")
    ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True, show_log=False)
    print("✓ PaddleOCR downloaded")
except Exception as e:
    print(f"⚠ PaddleOCR download failed (will auto-download on first use): {e}")
EOF

echo -e "${GREEN}✓${NC} Model pre-download complete"

# Start Redis
echo ""
echo -e "${BLUE}Starting Redis...${NC}"
redis-server --daemonize yes
sleep 2
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis is running"
else
    echo -e "${RED}✗${NC} Redis failed to start"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo -e "${GREEN}  INSTALLATION COMPLETE!${NC}"
echo "════════════════════════════════════════════════════════"
echo ""
echo "To start the API:"
echo -e "${BLUE}  python3 -m uvicorn services.api.api:app --host 0.0.0.0 --port 8000${NC}"
echo ""
echo "Or run in background:"
echo -e "${BLUE}  nohup python3 -m uvicorn services.api.api:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &${NC}"
echo ""
echo "Check GPU:"
echo -e "${BLUE}  nvidia-smi${NC}"
echo ""
