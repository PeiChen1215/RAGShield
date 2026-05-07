#!/bin/bash
# scripts/setup.sh — 本地开发环境一键初始化

set -e

echo "=== RAGShield 开发环境初始化 ==="

# 1. 检查 Python 版本
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "[1/6] Python 版本: $PYTHON_VERSION"
if ! python -c "import sys; assert sys.version_info[:2] == (3, 10)"; then
    echo "错误: 需要 Python 3.10，当前为 $PYTHON_VERSION"
    echo "建议: conda create -n ragshield python=3.10"
    exit 1
fi

# 2. 安装依赖
echo "[2/6] 安装依赖..."
pip install -q -r requirements.txt
pip install -q -r requirements-dev.txt

# 3. 配置环境变量
echo "[3/6] 检查环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "警告: 已创建 .env 模板，请编辑填入实际 API Key"
fi

# 4. 预下载模型
echo "[4/6] 预下载模型（首次需要 5-10 分钟）..."
if [ ! -d "$HOME/.cache/huggingface" ]; then
    python scripts/download_models.py
else
    echo "模型缓存已存在，跳过下载"
fi

# 5. 导入测试数据
echo "[5/6] 导入测试数据..."
python scripts/seed_data.py

# 6. 运行冒烟测试
echo "[6/6] 运行冒烟测试..."
pytest tests/ -m smoke -q

echo ""
echo "=== 初始化完成 ==="
echo "启动命令:"
echo "  uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000"
echo "  python src/frontend/app.py"
echo ""
echo "验证命令:"
echo "  curl http://localhost:8000/api/v1/health"
