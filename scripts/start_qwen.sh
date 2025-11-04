#!/bin/bash
#
# Qwen-VL SGLang Server Startup Script
# Starts the Qwen server on a free port with memory cap and healthcheck
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration (can be overridden by environment variables)
QWEN_PORT=${QWEN_PORT:-8123}
QWEN_MODEL=${QWEN_MODEL:-"Qwen/Qwen3-VL-8B-Instruct"}
QWEN_MEM_FRACTION=${QWEN_MEM_FRACTION:-0.50}
QWEN_LOG=${QWEN_LOG:-"qwen_sglang.log"}
HEALTHCHECK_TIMEOUT=${HEALTHCHECK_TIMEOUT:-60}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Qwen-VL SGLang Server Startup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo -e "  Model:          ${QWEN_MODEL}"
echo -e "  Port:           ${QWEN_PORT}"
echo -e "  Memory Fraction: ${QWEN_MEM_FRACTION}"
echo -e "  Log File:       ${QWEN_LOG}"
echo ""

# Kill any existing SGLang servers
echo -e "${YELLOW}Checking for existing SGLang servers...${NC}"
if pgrep -f "sglang.launch_server" > /dev/null; then
    echo -e "${YELLOW}Found existing SGLang process, killing...${NC}"
    pkill -f "sglang.launch_server" || true
    sleep 2
    echo -e "${GREEN}✓ Killed existing servers${NC}"
else
    echo -e "${GREEN}✓ No existing servers found${NC}"
fi

# Check if port is available
if lsof -Pi :${QWEN_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}✗ Port ${QWEN_PORT} is already in use!${NC}"
    echo -e "${RED}  Please choose a different port or free up ${QWEN_PORT}${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Port ${QWEN_PORT} is available${NC}"

# Check if model exists in cache
MODEL_PATH="/workspace/model_cache/hf/models--$(echo ${QWEN_MODEL} | sed 's/\//-/g')"
if [ ! -d "${MODEL_PATH}" ]; then
    echo -e "${YELLOW}⚠ Model not found in cache, will download on first run${NC}"
    echo -e "${YELLOW}  This may take 5-10 minutes...${NC}"
fi

# Start SGLang server
echo ""
echo -e "${GREEN}🚀 Starting SGLang server...${NC}"
nohup python -m sglang.launch_server \
    --model-path "${QWEN_MODEL}" \
    --host 127.0.0.1 \
    --port "${QWEN_PORT}" \
    --dtype auto \
    --mem-fraction-static "${QWEN_MEM_FRACTION}" \
    > "${QWEN_LOG}" 2>&1 &

SERVER_PID=$!
echo -e "${GREEN}✓ Server started (PID: ${SERVER_PID})${NC}"
echo -e "${BLUE}  Log: tail -f ${QWEN_LOG}${NC}"
echo ""

# Wait for server to be ready (healthcheck loop)
echo -e "${YELLOW}⏳ Waiting for server to be ready...${NC}"
HEALTH_URL="http://127.0.0.1:${QWEN_PORT}/v1/chat/completions"

for i in $(seq 1 ${HEALTHCHECK_TIMEOUT}); do
    sleep 2
    
    # Check if process is still alive
    if ! kill -0 ${SERVER_PID} 2>/dev/null; then
        echo -e "${RED}✗ Server process died! Check logs:${NC}"
        echo -e "${RED}  tail -n 50 ${QWEN_LOG}${NC}"
        tail -n 50 "${QWEN_LOG}"
        exit 1
    fi
    
    # Try to ping the server
    if curl -s -X POST "${HEALTH_URL}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer EMPTY" \
        -d "{
            \"model\": \"${QWEN_MODEL}\",
            \"messages\": [{\"role\": \"user\", \"content\": \"test\"}],
            \"max_tokens\": 1
        }" > /dev/null 2>&1; then
        
        echo -e "${GREEN}✓ Server is healthy and responding!${NC}"
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  Qwen-VL Server Ready${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "${BLUE}API Base: http://127.0.0.1:${QWEN_PORT}/v1${NC}"
        echo -e "${BLUE}PID:      ${SERVER_PID}${NC}"
        echo -e "${BLUE}Logs:     tail -f ${QWEN_LOG}${NC}"
        echo ""
        echo -e "${GREEN}Export these environment variables:${NC}"
        echo -e "  export QWEN_API_BASE=\"http://127.0.0.1:${QWEN_PORT}/v1\""
        echo -e "  export QWEN_MODEL=\"${QWEN_MODEL}\""
        echo ""
        exit 0
    fi
    
    # Progress indicator
    if [ $((i % 5)) -eq 0 ]; then
        echo -e "${YELLOW}  Still waiting... (${i}/${HEALTHCHECK_TIMEOUT}s)${NC}"
    fi
done

# Timeout reached
echo -e "${RED}✗ Server failed to respond within ${HEALTHCHECK_TIMEOUT} seconds${NC}"
echo -e "${RED}  Check logs for errors:${NC}"
echo -e "${RED}  tail -n 100 ${QWEN_LOG}${NC}"
echo ""
echo -e "${YELLOW}Recent log entries:${NC}"
tail -n 50 "${QWEN_LOG}"
exit 1
