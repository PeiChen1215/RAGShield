#!/bin/bash
# scripts/start.sh — 容器入口脚本，同时启动 FastAPI + Gradio

set -e

echo "=== RAGShield 启动 ==="

# 启动 FastAPI（业务核心，后台运行）
echo "[1/2] 启动 FastAPI (port 8000)..."
uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info &

FASTAPI_PID=$!
echo "FastAPI PID: $FASTAPI_PID"

# 等待 FastAPI 健康检查通过
echo "等待 FastAPI 就绪..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "FastAPI 就绪"
        break
    fi
    sleep 1
done

# 启动 Gradio（纯界面层，后台运行）
echo "[2/2] 启动 Gradio (port 7860)..."
python src/frontend/app.py &

GRADIO_PID=$!
echo "Gradio PID: $GRADIO_PID"

# 捕获终止信号，优雅关闭
cleanup() {
    echo "收到终止信号，正在关闭..."
    kill $GRADIO_PID 2>/dev/null || true
    kill $FASTAPI_PID 2>/dev/null || true
    wait
    echo "已关闭"
}
trap cleanup SIGTERM SIGINT

# 保持脚本运行
wait
