#!/bin/bash
set -e

echo "🚀 Starting Framely-Eyes on RunPod..."
echo "======================================"

# Check GPU
if nvidia-smi &> /dev/null; then
    echo "✅ GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "⚠️  No GPU detected - running in CPU mode"
fi

# Initialize models if not already cached
echo ""
echo "📦 Initializing models..."
python3 -c "
from services.utils.model_manager import initialize_models
import logging
logging.basicConfig(level=logging.INFO)
results = initialize_models()
failed = [k for k, v in results.items() if not v]
if failed:
    print(f'⚠️  Some models failed: {failed}')
    print('⚠️  System will continue with available models')
else:
    print('✅ All models initialized successfully')
"

# Start Redis (if not already running)
if ! pgrep redis-server > /dev/null; then
    echo ""
    echo "🔄 Starting Redis..."
    redis-server --daemonize yes --bind 127.0.0.1 --port 6379
    sleep 2
fi

# Check if Qwen-VL service is needed locally or separate
if [ "$QWEN_LOCAL" = "true" ]; then
    echo ""
    echo "🤖 Starting Qwen-VL service..."
    # Start vLLM in background
    python3 -m vllm.entrypoints.openai.api_server \
        --model Qwen/Qwen2.5-VL-7B-Instruct \
        --quantization awq \
        --max-model-len 8192 \
        --gpu-memory-utilization 0.5 \
        --port 8001 \
        --host 0.0.0.0 &
    
    QWEN_PID=$!
    echo "Qwen-VL started with PID: $QWEN_PID"
    sleep 10
fi

# Start API server
echo ""
echo "🌐 Starting Framely-Eyes API..."
echo "======================================"
exec uvicorn services.api.api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    --access-log \
    --use-colors
