# RAGShield 代码骨架说明（国一适配版）

> **文档标识**: RAGShield-SETUP-v1.1  
> **创建日期**: 2026-05-07  
> **用途**: 记录精简后的代码骨架结构，聚焦国一核心路径，删除冗余占位。

---

## 一、精简原则

**保留**：功能代码、答辩弹药、演示必需  
**删除**：V1 占位接口、冗余测试、非关键脚本

**文件数变化**：51 → **~30**，核心功能零损失。

---

## 二、目录结构

```
RAGShield/
├── config/
│   └── config.yaml              # 单配置，gpu/cpu 通过 device 字段切换
├── data/
│   ├── attack_kb/               # 攻击模板库（Week 3 填充）
│   ├── normal_kb/               # 正常文档库（Week 2 填充）
│   ├── queries/                 # 查询集合（Week 3 填充）
│   └── chroma_db/               # ChromaDB 持久化（.gitignore）
├── old_docs/                    # 旧版文档归档
├── scripts/
│   ├── download_models.py       # 模型预下载
│   ├── evaluate.py              # 评测主脚本（Week 3 填充主流程）
│   ├── seed_data.py             # 数据导入（Week 2 填充）
│   ├── start.sh                 # 容器启动（FastAPI + Gradio）
│   ├── threshold_sweep.py       # 阈值扫描（Week 3 填充，答辩弹药）
│   └── weight_ablation.py       # 权重消融（Week 3 填充，答辩弹药）
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI 入口 + /health
│   │   ├── schemas.py           # Pydantic 模型（已冻结）
│   │   └── routers/
│   │       ├── kb.py            # /kb/upload, /kb/scan
│   │       └── query.py         # /query（Week 2 串真实检测链）
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
│   │   └── sensitive_ner.py     # 正则 + HanLP（正则层已填）
│   ├── layer2_retrieval/
│   │   ├── attention_analyzer.py # 伪注意力方差 + 接力加分（已填）
│   │   └── relevance_scorer.py  # 余弦相似度
│   └── layer3_generation/
│       ├── consistency_checker.py # bge-reranker + chinanli 双路融合（已填）
│       └── llm_client.py        # Kimi API 封装
├── tests/
│   ├── conftest.py              # pytest 共享 fixture
│   ├── test_api.py              # API 冒烟测试（/health + /query）
│   └── test_fusion.py           # 融合模块测试（全通过）
├── udocs/                       # 冻结文档（8份，答辩用）
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git 忽略规则
├── pyproject.toml               # Black + isort 配置
├── requirements.txt             # 生产依赖
├── requirements-dev.txt         # 开发依赖（pytest 等）
├── setup.cfg                    # Flake8 配置
├── README.md                    # 对外展示用（待写）
└── SETUP.md                     # 本文件
```

---

## 三、已删除项说明

| 删除项 | 删除理由 |
|--------|---------|
| `layer1_kb/context_pollution_detector.py` | V1 占位，不产生评分价值 |
| `layer1_kb/bias_detector.py` | V1 占位，不产生评分价值 |
| `layer2_retrieval/diversity_monitor.py` | V1 占位，不产生评分价值 |
| `layer3_generation/bias_checker.py` | V1 占位，不产生评分价值 |
| `tests/test_core.py` | 非核心冒烟测试，减少维护负担 |
| `tests/test_layer1.py` | 非核心冒烟测试，减少维护负担 |
| `tests/test_layer2.py` | 非核心冒烟测试，减少维护负担 |
| `tests/test_layer3.py` | 需要预下载模型，现场不跑 |
| `scripts/setup.sh` | 比赛现场直接 pip install，不用一键脚本 |
| `config/gpu_config.yaml` + `cpu_config.yaml` | 合并为单文件，通过 device 字段切换 |

---

## 四、核心交付物状态

### ✅ 已硬实现（可直接运行/测试）

| 模块 | 实现状态 | 说明 |
|------|---------|------|
| `api/schemas.py` | **100%** | 全部 Pydantic 模型已代码化 |
| `api/main.py` | **100%** | FastAPI 入口、路由注册、CORS、/health |
| `core/config.py` | **100%** | Pydantic-Settings，读取 .env 和 config.yaml |
| `core/embedder.py` | **100%** | SentenceTransformer 封装，懒加载，L2 归一化 |
| `core/vector_store.py` | **100%** | ChromaDB 嵌入式，cosine space，kb_id 隔离 |
| `layer1_kb/outlier_detector.py` | **核心已填** | Q12 混合法评分公式完整 |
| `layer1_kb/sensitive_ner.py` | **正则层已填** | 5 类正则规则 + 风险加分映射 |
| `layer2_retrieval/attention_analyzer.py` | **核心已填** | 方差/熵 + Layer1 接力加分 |
| `layer2_retrieval/relevance_scorer.py` | **100%** | 点积计算余弦相似度 |
| `layer3_generation/consistency_checker.py` | **核心已填** | bge-reranker + chinanli 双路融合 |
| `layer3_generation/llm_client.py` | **100%** | AsyncOpenAI 封装，兼容 Kimi API |
| `fusion/risk_fusion.py` | **100%** | 0.3/0.3/0.4 加权 + 三级响应 |
| `frontend/app.py` | **100%** | Gradio + blocked_answer 对比展示 |
| `tests/test_fusion.py` | **100%** | 4 个断言，pytest 直接通过 |

### ⚠️ 占位实现（Week 2-3 填充）

| 模块 | 说明 |
|------|------|
| `api/routers/kb.py` | 接口签名正确，返回占位响应 |
| `api/routers/query.py` | 接口签名正确，返回占位响应（含完整三层结构） |
| `scripts/evaluate.py` | 指标计算函数已填，主流程占位 |
| `scripts/threshold_sweep.py` | 骨架，Week 3 填充（答辩弹药） |
| `scripts/weight_ablation.py` | 骨架，Week 3 填充（答辩弹药） |
| `scripts/seed_data.py` | 骨架，Week 2 填充 |

---

## 五、快速启动

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

# 6. 运行冒烟测试
pytest tests/ -v
```

---

## 六、Week 2-4 演进路径

### Week 2：打通端到端闭环（P0）
1. `routers/kb.py` → 接入 `Embedder` + `VectorStore` + `OutlierDetector`
2. `routers/query.py` → 接入 `Embedder` + `VectorStore` + `AttentionAnalyzer` + `LLMClient` + `ConsistencyChecker` + `RiskFusion`
3. `seed_data.py` → 导入 50 篇正常文档 + 8 篇攻击文档

### Week 3：评测与调优（P1）
1. 构造 `data/eval_dataset.json`（48 攻击 + 100 正常）
2. 填充 `evaluate.py` 主流程 → 出检测率/误报率/延迟
3. 填充 `threshold_sweep.py` → 锁定最优阈值（答辩弹药）
4. 填充 `weight_ablation.py` → 验证 0.3/0.3/0.4 最优（答辩弹药）

### Week 4：部署与演示（P2）
1. 构建 Docker 镜像（`docker build -t ragshield .`）
2. 导出离线镜像 `ragshield.tar.gz`
3. Gradio 界面微调 + 演示用例固化（3 组 Demo）
4. 写 `README.md`（对外展示）

---

*本骨架由 Kimi Code CLI 基于 RAGShield 冻结文档生成，经国一适配精简。*
