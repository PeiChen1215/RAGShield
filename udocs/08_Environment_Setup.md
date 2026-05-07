# RAGShield 开发环境统一指南

> **文档标识**: RAGShield-ENV-v1.0  
> **文档状态**: 已冻结  
> **创建日期**: 2026-04-28  
> **目标读者**: 三人开发团队、新加入成员、比赛现场部署人员  
> **用途**: 确保任一队员换电脑/比赛现场新设备，30 分钟内能跑通完整系统。

---

## 一、文档控制

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0 | 2026-04-28 | 团队 | 初始版本，覆盖 Conda 环境、Docker 部署、模型预下载、验证清单 |

---

## 二、环境要求

| 组件 | 版本/规格 | 用途 | 备注 |
|------|----------|------|------|
| **操作系统** | Linux (Ubuntu 22.04+) / macOS / Windows WSL2 | 开发/部署 | 推荐 Ubuntu，比赛现场通常提供 |
| **Python** | 3.10.x | 运行时 | 精确版本，不兼容 3.11+ 部分依赖 |
| **Conda** | Miniconda3 最新版 | 环境管理 | 比 Anaconda 轻量 |
| **Docker** | 24.0+ | 部署打包 | 比赛现场用 |
| **Git** | 2.40+ | 版本控制 | — |
| **GPU** | NVIDIA RTX 3060+ / 4060 (可选) | 模型推理加速 | CPU 版可运行，延迟增加 |
| **内存** | ≥ 16GB RAM | 模型加载 | BGE-M3 (~2GB) + reranker (~1GB) + 系统 |
| **磁盘** | ≥ 20GB 可用 | 模型 + 数据 | Docker 镜像占用 |

---

## 三、本地开发环境搭建

### 3.1 步骤 1：安装 Miniconda

```bash
# Linux / WSL2
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# 按提示安装，建议选择 "yes" 初始化 conda

# macOS (Intel)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh

# macOS (Apple Silicon / M1/M2)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
bash Miniconda3-latest-MacOSX-arm64.sh

# 安装完成后重启终端，验证
conda --version  # 应显示 conda 24.x.x
```

### 3.2 步骤 2：创建 Conda 环境

```bash
# 创建环境（指定 Python 3.10）
conda create -n ragshield python=3.10 -y

# 激活环境
conda activate ragshield

# 验证 Python 版本
python --version  # Python 3.10.x
```

### 3.3 步骤 3：克隆仓库并安装依赖

```bash
# 克隆仓库（替换为实际仓库地址）
git clone https://github.com/yourteam/RAGShield.git
cd RAGShield

# 安装生产依赖
pip install -r requirements.txt

# 安装开发依赖（代码格式化、测试）
pip install -r requirements-dev.txt

# 验证关键依赖版本
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import chromadb; print(f'ChromaDB: {chromadb.__version__}')"
python -c "import sklearn; print(f'scikit-learn: {sklearn.__version__}')"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
```

### 3.4 步骤 4：配置环境变量

```bash
# 复制模板文件
cp .env.example .env

# 编辑 .env，填入实际 API Key
nano .env
```

`.env` 文件内容：
```bash
# === RAGShield 环境变量 ===

# LLM API 配置（必填其一）
KIMI_API_KEY=sk-your-actual-key-here
KIMI_BASE_URL=https://api.moonshot.cn/v1

# 备用 LLM API（可选）
# DEEPSEEK_API_KEY=sk-your-backup-key-here

# 模型配置
DEFAULT_MODEL_PROFILE=cpu      # gpu 或 cpu
EMBEDDING_DEVICE=cpu           # cuda 或 cpu

# 检测阈值（可被 threshold_sweep.py 覆盖）
IF_CONTAMINATION=0.1
LOF_N_NEIGHBORS=20
NLI_SIMILARITY_THRESHOLD=0.3
```

### 3.5 步骤 5：预下载模型（本地开发）

```bash
# 运行模型预下载脚本（首次运行需要 5-10 分钟，取决于网络）
python scripts/download_models.py

# 脚本会自动下载到 ~/.cache/huggingface/
# 下载列表：
# - BAAI/bge-m3 (GPU 版) 或 BAAI/bge-small-zh-v1.5 (CPU 版)
# - BAAI/bge-reranker-large
# - uer/roberta-base-finetuned-chinanli-chinese
# - HanLP 预训练模型
```

`scripts/download_models.py` 参考实现：
```python
#!/usr/bin/env python3
"""预下载所有模型到本地缓存，避免运行时网络依赖。"""

import os
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import hanlp

# 根据配置选择模型
PROFILE = os.getenv("DEFAULT_MODEL_PROFILE", "cpu")

MODELS = {
    "embedding": "BAAI/bge-m3" if PROFILE == "gpu" else "BAAI/bge-small-zh-v1.5",
    "reranker": "BAAI/bge-reranker-large",
    "nli": "uer/roberta-base-finetuned-chinanli-chinese",
}

def download():
    print(f"=== 当前模型配置: {PROFILE} ===")
    
    print(f"[1/4] 下载嵌入模型: {MODELS['embedding']}")
    SentenceTransformer(MODELS["embedding"])
    
    print(f"[2/4] 下载重排序模型: {MODELS['reranker']}")
    SentenceTransformer(MODELS["reranker"])
    
    print(f"[3/4] 下载 NLI 模型: {MODELS['nli']}")
    AutoTokenizer.from_pretrained(MODELS["nli"])
    AutoModelForSequenceClassification.from_pretrained(MODELS["nli"])
    
    print("[4/4] 下载 HanLP 模型")
    hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)
    
    print("=== 所有模型下载完成 ===")

if __name__ == "__main__":
    download()
```

### 3.6 步骤 6：导入测试数据并启动服务

```bash
# 一键导入测试数据
python scripts/seed_data.py

# 启动 FastAPI（开发模式，热重载）
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 另开终端，启动 Gradio 界面
conda activate ragshield
python src/frontend/app.py
```

### 3.7 步骤 7：验证环境

```bash
# 运行健康检查
curl http://localhost:8000/api/v1/health

# 运行冒烟测试
pytest tests/ -m smoke -v

# 运行单次查询测试
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "年假有多少天", "kb_id": "default"}'
```

**验证通过标准**：
- [ ] `curl /health` 返回 `{"status": "ok"}`
- [ ] `pytest` 冒烟测试全部通过
- [ ] 单次查询返回 JSON，包含 `final_risk_score` 和 `risk_level`

---

## 四、一键初始化脚本（setup.sh）

将上述步骤封装为自动化脚本，新成员执行一行命令即可：

```bash
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
```

**使用方法**：
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

---

## 五、Docker 部署指南

### 5.1 构建镜像

```bash
# 构建 GPU 版镜像（含 BGE-M3）
docker build -t ragshield:gpu --build-arg MODEL_PROFILE=gpu .

# 构建 CPU 版镜像（含 bge-small-zh，更小）
docker build -t ragshield:cpu --build-arg MODEL_PROFILE=cpu .

# 查看镜像大小
docker images ragshield
```

### 5.2 Dockerfile（参考实现）

```dockerfile
# Dockerfile
FROM python:3.10-slim

ARG MODEL_PROFILE=cpu
ENV MODEL_PROFILE=${MODEL_PROFILE}

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 预下载模型（构建时完成）
COPY scripts/download_models.py ./scripts/
RUN python scripts/download_models.py

# 复制源码
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/
COPY scripts/start.sh ./scripts/
RUN chmod +x scripts/start.sh

# 环境变量
ENV PYTHONPATH=/app
ENV CONFIG_PATH=/app/config/${MODEL_PROFILE}_config.yaml

# 暴露端口
EXPOSE 8000 7860

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动
CMD ["./scripts/start.sh"]
```

### 5.3 导出离线镜像（比赛现场用）

```bash
# 导出 CPU 版（推荐，体积小）
docker save ragshield:cpu | gzip > ragshield-cpu.tar.gz
# 约 1.2-1.8GB（含 gzip 压缩）

# 导出 GPU 版
docker save ragshield:gpu | gzip > ragshield-gpu.tar.gz
# 约 2.5-3.5GB

# 现场恢复（30 秒内启动）
gunzip -c ragshield-cpu.tar.gz | docker load
docker run -d -p 8000:8000 -p 7860:7860 --name ragshield ragshield:cpu
```

### 5.4 docker-compose.yml

```yaml
version: "3.8"

services:
  ragshield:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        MODEL_PROFILE: cpu
    image: ragshield:cpu
    container_name: ragshield
    ports:
      - "8000:8000"
      - "7860:7860"
    environment:
      - KIMI_API_KEY=${KIMI_API_KEY}
      - DEFAULT_MODEL_PROFILE=cpu
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

---

## 六、比赛现场快速恢复流程

```bash
# 步骤 1: 加载镜像（U 盘或云盘拷贝到比赛机器）
gunzip -c ragshield-cpu.tar.gz | docker load

# 步骤 2: 启动容器
docker run -d \
  -p 8000:8000 \
  -p 7860:7860 \
  --name ragshield \
  -e KIMI_API_KEY=sk-xxx \
  ragshield:cpu

# 步骤 3: 验证启动（等待 60 秒模型加载）
sleep 60
curl http://localhost:8000/api/v1/health

# 步骤 4: 浏览器打开演示界面
# FastAPI Swagger: http://localhost:8000/docs
# Gradio 界面: http://localhost:7860
```

---

## 七、常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `ModuleNotFoundError: No module named 'xxx'` | 依赖未安装或 Conda 环境未激活 | `conda activate ragshield && pip install -r requirements.txt` |
| `torch.cuda.is_available() == False` | CUDA 驱动不匹配或 PyTorch CPU 版 | 检查 `nvidia-smi`，或使用 CPU 版配置 |
| `OSError: [Errno 28] No space left` | 磁盘不足，模型缓存过大 | 清理 `~/.cache/huggingface/` 或扩展磁盘 |
| `ConnectionError` to Kimi API | 网络不通或 API Key 无效 | 检查 `.env` 中 `KIMI_API_KEY`，或切换 DeepSeek fallback |
| BGE-M3 加载极慢（>5分钟） | 首次下载模型 | 正常现象，后续从缓存加载。比赛时确保镜像已预装 |
| Gradio 界面空白 | 端口冲突或前端未启动 | 检查 `netstat -tlnp \| grep 7860`，重启前端服务 |
| ChromaDB `lock` 错误 | 多进程同时访问（忘记 --workers 1） | 停止服务，用 `--workers 1` 重启 |
| Layer1 标红结果丢失 | 服务重启后内存中的标红表被清空 | 正常现象，重新上传文档或调用 `GET /kb/scan` 触发扫描即可恢复 |
| pytest 全部跳过 | 未标记 smoke | 运行 `pytest tests/ -m smoke -v` |

---

## 八、验证清单（进入开发期前必须完成）

| # | 检查项 | 验证命令 | 通过标准 |
|---|--------|---------|---------|
| 1 | Python 版本 | `python --version` | 3.10.x |
| 2 | Conda 环境 | `conda env list` | ragshield 存在且激活 |
| 3 | 依赖安装 | `pip list | grep fastapi` | fastapi >= 0.115 |
| 4 | 环境变量 | `cat .env | grep KIMI` | API Key 已填写 |
| 5 | 模型缓存 | `ls ~/.cache/huggingface/` | 包含 BGE-M3 或 bge-small |
| 6 | 测试数据 | `ls data/chroma_db/` | 存在持久化数据 |
| 7 | FastAPI 启动 | `curl http://localhost:8000/api/v1/health` | `{"status": "ok"}` |
| 8 | Gradio 启动 | `curl http://localhost:7860` | 返回 HTML |
| 9 | 冒烟测试 | `pytest tests/ -m smoke -v` | 全部 PASS |
| 10 | 单次查询 | `curl /query` | 返回 JSON 含 risk_score |
| 11 | Docker 构建 | `docker images | grep ragshield` | 镜像存在 |
| 12 | 离线恢复 | `docker load < ragshield-cpu.tar.gz` | 加载成功 |
| 13 | Layer1 缓存 | `ls data/layer1_scan_cache_*.jsonl` | 存在（可选，服务重启后恢复用） |

**全部 12 项通过 → 环境就绪，可进入 Sprint 开发。**

---

*文档版本: v1.0 | 状态: 已冻结 | 下次评审: Week 4 里程碑验收会*
