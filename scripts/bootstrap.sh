#!/bin/bash
#
# Framely-Eyes Bootstrap Script
# One-command setup: loads env, restores caches, starts services, validates readiness
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo -e "${BOLD}${BLUE}========================================${NC}"
echo -e "${BOLD}${BLUE}  Framely-Eyes Bootstrap${NC}"
echo -e "${BOLD}${BLUE}========================================${NC}"
echo ""

# Step 1: Load environment variables
echo -e "${BLUE}[1/5] Loading environment configuration...${NC}"
if [ -f "${PROJECT_ROOT}/.env" ]; then
    source "${PROJECT_ROOT}/.env"
    echo -e "${GREEN}✓ Loaded .env${NC}"
elif [ -f "${PROJECT_ROOT}/.env.example" ]; then
    echo -e "${YELLOW}⚠ .env not found, using .env.example defaults${NC}"
    source "${PROJECT_ROOT}/.env.example"
else
    echo -e "${RED}✗ No .env or .env.example found${NC}"
    echo -e "${RED}  Please create .env from .env.example${NC}"
    exit 1
fi
echo ""

# Step 2: Restore model caches (if missing)
echo -e "${BLUE}[2/5] Checking model caches...${NC}"

# Check if model cache directory exists
if [ -d "/workspace/model_cache" ]; then
    echo -e "${GREEN}✓ Model cache exists at /workspace/model_cache${NC}"
else
    # Try to restore from tarball
    if ls /workspace/model_caches_*.tgz 1> /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Model cache missing, restoring from backup...${NC}"
        cd /workspace
        tar -xzf model_caches_*.tgz
        echo -e "${GREEN}✓ Model cache restored${NC}"
    else
        echo -e "${YELLOW}⚠ No model cache found (first run)${NC}"
        echo -e "${YELLOW}  Models will be downloaded on first use${NC}"
        mkdir -p /workspace/model_cache/{hf,torch,ultralytics,insightface}
    fi
fi

# Ensure cache directories exist
mkdir -p "${HF_HOME:-/workspace/model_cache/hf}"
mkdir -p "${TORCH_HOME:-/workspace/model_cache/torch}"
mkdir -p /workspace/model_cache/insightface

# Link InsightFace cache if it exists
if [ -d "/workspace/model_cache/insightface" ] && [ ! -d "/root/.insightface" ]; then
    echo -e "${YELLOW}  Linking InsightFace cache...${NC}"
    mkdir -p /root/.insightface
    cp -a /workspace/model_cache/insightface/. /root/.insightface/ 2>/dev/null || true
    echo -e "${GREEN}  ✓ InsightFace cache linked${NC}"
fi

echo ""

# Step 3: Verify Python environment
echo -e "${BLUE}[3/5] Verifying Python environment...${NC}"
if ! python --version > /dev/null 2>&1; then
    echo -e "${RED}✗ Python not found${NC}"
    exit 1
fi
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python ${PYTHON_VERSION}${NC}"

# Check critical packages
MISSING_PACKAGES=()
for pkg in torch cv2 numpy ultralytics; do
    if ! python -c "import ${pkg}" 2>/dev/null; then
        MISSING_PACKAGES+=("${pkg}")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${RED}✗ Missing Python packages: ${MISSING_PACKAGES[*]}${NC}"
    echo -e "${YELLOW}  Run: pip install -r requirements.txt${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Critical packages installed${NC}"
echo ""

# Step 4: Start Qwen-VL server
echo -e "${BLUE}[4/5] Starting Qwen-VL server...${NC}"
if [ "${QWEN_ENABLED}" == "1" ]; then
    # Make script executable
    chmod +x "${SCRIPT_DIR}/start_qwen.sh"
    
    # Check if already running
    if curl -s -X POST "http://127.0.0.1:${QWEN_PORT:-8123}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer EMPTY" \
        -d '{"model":"test","messages":[{"role":"user","content":"test"}],"max_tokens":1}' \
        > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Qwen server already running on port ${QWEN_PORT:-8123}${NC}"
    else
        # Start the server
        if ! "${SCRIPT_DIR}/start_qwen.sh"; then
            echo -e "${RED}✗ Failed to start Qwen server${NC}"
            echo -e "${YELLOW}  Pipeline can still run with QWEN_ENABLED=0${NC}"
            echo -e "${YELLOW}  To skip Qwen: export QWEN_ENABLED=0${NC}"
            read -p "Continue without Qwen? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            export QWEN_ENABLED=0
        fi
    fi
else
    echo -e "${YELLOW}⚠ Qwen disabled (QWEN_ENABLED=0)${NC}"
    echo -e "${YELLOW}  Pipeline will skip vision-language reasoning${NC}"
fi
echo ""

# Step 5: Validate setup
echo -e "${BLUE}[5/5] Validating setup...${NC}"

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.free --format=csv,noheader,nounits 2>/dev/null | head -n 1)
    if [ -n "${GPU_INFO}" ]; then
        GPU_NAME=$(echo "${GPU_INFO}" | cut -d',' -f1)
        GPU_MEM=$(echo "${GPU_INFO}" | cut -d',' -f2)
        echo -e "${GREEN}✓ GPU: ${GPU_NAME} (${GPU_MEM} MB free)${NC}"
    else
        echo -e "${YELLOW}⚠ GPU detected but no memory info${NC}"
    fi
else
    echo -e "${RED}✗ No GPU detected (nvidia-smi not found)${NC}"
    echo -e "${YELLOW}  Pipeline will run in CPU-only mode (slow)${NC}"
fi

# Check storage space
STORE_DIR="${PROJECT_ROOT}/store"
mkdir -p "${STORE_DIR}"
FREE_SPACE=$(df -h "${STORE_DIR}" | tail -1 | awk '{print $4}')
echo -e "${GREEN}✓ Storage: ${FREE_SPACE} free in ${STORE_DIR}${NC}"

# Check Qwen connectivity (if enabled)
if [ "${QWEN_ENABLED}" == "1" ]; then
    if curl -s -X POST "${QWEN_API_BASE}/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer EMPTY" \
        -d "{\"model\":\"${QWEN_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"test\"}],\"max_tokens\":1}" \
        > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Qwen-VL server reachable at ${QWEN_API_BASE}${NC}"
    else
        echo -e "${YELLOW}⚠ Qwen server not responding (may still be loading)${NC}"
    fi
fi

echo ""
echo -e "${BOLD}${GREEN}========================================${NC}"
echo -e "${BOLD}${GREEN}  Bootstrap Complete!${NC}"
echo -e "${BOLD}${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Run test pipeline:    ${BOLD}python test_pipeline.py${NC}"
echo -e "  2. Analyze your video:   ${BOLD}python -m services.orchestrator.orchestrator <video_id> <video_path>${NC}"
echo -e "  3. Check results:        ${BOLD}cat store/<video_id>/vab.json${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo -e "  Qwen:         ${QWEN_ENABLED} (${QWEN_MODEL})"
echo -e "  API Base:     ${QWEN_API_BASE}"
echo -e "  Frame Stride: ${FRAME_STRIDE:-1}"
echo -e "  GPU Sem:      ${GPU_SEMAPHORE:-2}"
echo ""
echo -e "${GREEN}Happy analyzing! 🎬✨${NC}"
