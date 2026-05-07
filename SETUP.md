# RAGShield 代码骨架说明

> **文档标识**: RAGShield-SETUP-v1.0  
> **创建日期**: 2026-05-07  
> **用途**: 记录代码骨架结构、模块职责、以及从骨架到完整实现的演进路径。

---

## 一、骨架概览

本骨架基于 `udocs/` 下 8 份冻结文档构建，严格遵循 04_SAD（系统架构设计）和 06_DEVSTD（开发规范）。

**当前状态**：
- ✅ FastAPI 可启动（`uvicorn src.api.main:app --reload`）
- ✅ Swagger UI 自动生成（`http://localhost:8000/docs`）
- ✅ Pydantic 模型已代码化（`src/api/schemas.py`）
- ✅ 三层检测模块占位完成（接口签名 + docstring）
- ✅ 测试骨架完成（pytest + conftest + 6 个测试文件）
- ✅ Docker/部署脚本骨架完成
- ⚠️ 所有检测逻辑为**占位实现**，返回固定值

---

## 二、目录结构

```
RAGShield/
├── config/
│   ├── gpu_config.yaml          # GPU 版配置
│   └── cpu_config.yaml          # CPU 轻量化版配置
├── data/
│   ├── attack_kb/               # 攻击模板库（待填充）
│   ├── normal_kb/               # 正常文档库（待填充）
│   ├── queries/                 # 查询集合（待填充）
│   └── chroma_db/               # ChromaDB 持久化（.gitignore）
├── old_docs/                    # 旧版文档归档
├── scripts/
│   ├── download_models.py       # 模型预下载
│   ├── evaluate.py              # 评测主脚本（占位）
│   ├── seed_data.py             # 数据导入（占位）
│   ├── setup.sh                 # 一键初始化
│   ├── start.sh                 # 容器启动（FastAPI + Gradio）
│   ├── threshold_sweep.py       # 阈值扫描（占位）
│   └── weight_ablation.py       # 权重消融（占位）
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI 入口 + /health
│   │   ├── schemas.py           # Pydantic 模型（已冻结）
│   │   └── routers/
│   │       ├── kb.py            # /kb/upload, /kb/scan
│   │       └── query.py         # /query（占位响应）
│   ├── core/
│   │   ├── config.py            # Pydantic-Settings 配置
│   │   ├── embedder.py          # BGE-M3 / bge-small 封装
│   │   └── vector_store.py      # ChromaDB 封装（cosine space）
│   ├── frontend/
│   │   └── app.py               # Gradio 界面（HTTP 调用 FastAPI）
│   ├── fusion/
│   │   └── risk_fusion.py       # 三层加权融合（0.3/0.3/0.4）
│   ├── layer1_kb/
│   │   ├── outlier_detector.py  # IF + LOF + 余弦基线（评分公式已填）
│   │   ├── sensitive_ner.py     # 正则 + HanLP（正则层已填）
│   │   ├── context_pollution_detector.py  # V1 占位
│   │   └── bias_detector.py     # V1 占位
│   ├── layer2_retrieval/
│   │   ├── attention_analyzer.py # 伪注意力方差 + 接力加分（已填）
│   │   ├── relevance_scorer.py  # 余弦相似度
│   │   └── diversity_monitor.py # V1 占位
│   └── layer3_generation/
│       ├── consistency_checker.py # bge-reranker + chinanli（已填）
│       ├── llm_client.py        # Kimi API 封装
│       └── bias_checker.py      # V1 占位
├── tests/
│   ├── conftest.py              # pytest 共享 fixture
│   ├── test_api.py              # API 集成测试（含 /health 通过）
│   ├── test_core.py             # core 模块测试
│   ├── test_fusion.py           # 融合模块测试（全通过）
│   ├── test_layer1.py           # Layer1 测试（IF+LOF 可跑）
│   ├── test_layer2.py           # Layer2 测试（方差+接力 可跑）
│   └── test_layer3.py           # Layer3 测试（需模型）
├── udocs/                       # 冻结文档（8份）
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git 忽略规则
├── pyproject.toml               # Black + isort 配置
├── requirements.txt             # 生产依赖
├── requirements-dev.txt         # 开发依赖
├── setup.cfg                    # Flake8 配置
└── SETUP.md                     # 本文件
```

---

## 三、已实现 vs 待实现

### ✅ 已硬实现（可直接运行/测试）

| 模块 | 实现状态 | 说明 |
|------|---------|------|
| `api/schemas.py` | **100%** | 全部 Pydantic 模型已代码化，与 05_API_Contract 一一对应 |
| `api/main.py` | **100%** | FastAPI 入口、路由注册、CORS、/health、lifespan |
| `api/routers/kb.py` | **骨架** | 接口签名正确，返回占位响应 |
| `api/routers/query.py` | **骨架** | 接口签名正确，返回占位响应（含完整三层结构） |
| `core/config.py` | **100%** | Pydantic-Settings，读取 .env 和默认值 |
| `core/embedder.py` | **100%** | SentenceTransformer 封装，懒加载，L2 归一化 |
| `core/vector_store.py` | **100%** | ChromaDB 嵌入式，cosine space，kb_id 隔离 |
| `layer1_kb/outlier_detector.py` | **核心已填** | Q12 混合法评分公式完整（IF+LOF+余弦基线） |
| `layer1_kb/sensitive_ner.py` | **正则层已填** | 5 类正则规则 + 风险加分映射 |
| `layer2_retrieval/attention_analyzer.py` | **核心已填** | 方差/熵计算 + Layer1 接力加分（+0.15/篇） |
| `layer2_retrieval/relevance_scorer.py` | **100%** | 点积计算余弦相似度 |
| `layer3_generation/consistency_checker.py` | **核心已填** | bge-reranker + chinanli 双路融合逻辑完整 |
| `layer3_generation/llm_client.py` | **100%** | AsyncOpenAI 封装，兼容 Kimi API |
| `fusion/risk_fusion.py` | **100%** | 0.3/0.3/0.4 加权 + safe/warning/danger 分级 |
| `frontend/app.py` | **100%** | Gradio 界面，HTTP 调用，blocked_answer 对比展示 |
| `tests/` | **骨架** | 6 个测试文件，conftest 含 fixture，test_fusion 全通过 |

### ⚠️ 占位实现（V1 预留接口）

| 模块 | 说明 |
|------|------|
| `layer1_kb/context_pollution_detector.py` | 返回 `detected: false, risk_score: 0.0` |
| `layer1_kb/bias_detector.py` | 返回 `detected: false, risk_score: 0.0` |
| `layer2_retrieval/diversity_monitor.py` | 返回 `diversity_score: 0.0` |
| `layer3_generation/bias_checker.py` | 返回 `detected: false, risk_score: 0.0` |
| `scripts/evaluate.py` | 评测指标计算函数已填，主流程占位 |
| `scripts/threshold_sweep.py` | 骨架 |
| `scripts/weight_ablation.py` | 骨架 |
| `scripts/seed_data.py` | 骨架 |

---

## 四、快速启动

```bash
# 1. 创建 Conda 环境
conda create -n ragshield python=3.10 -y
conda activate ragshield

# 2. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 KIMI_API_KEY

# 4. 启动 FastAPI（单 worker，避免 ChromaDB 锁冲突）
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 --workers 1

# 5. 浏览器打开 Swagger UI
open http://localhost:8000/docs
```

---

## 五、Week 2-4 演进路径

### Week 2：打通端到端闭环
1. `routers/kb.py`：接入 `Embedder` + `VectorStore` + `OutlierDetector`
2. `routers/query.py`：接入 `Embedder` + `VectorStore` + `AttentionAnalyzer` + `LLMClient` + `ConsistencyChecker` + `RiskFusion`
3. `seed_data.py`：导入 50 篇正常文档 + 8 篇攻击文档到默认知识库

### Week 3：评测与调优
1. 构造 `data/eval_dataset.json`（48 攻击 + 100 正常）
2. 跑通 `evaluate.py` + `threshold_sweep.py`
3. 锁定最优阈值参数，写入 `.env`

### Week 4：部署与演示
1. 构建 Docker 镜像（`ragshield:cpu` / `ragshield:gpu`）
2. 导出离线镜像 `ragshield-cpu.tar.gz`
3. Gradio 界面微调 + 演示用例固化

---

*本骨架由 Kimi Code CLI 基于 RAGShield 冻结文档自动生成。*
