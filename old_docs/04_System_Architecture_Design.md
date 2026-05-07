# RAGShield 系统架构设计文档 (SAD)

> **文档标识**: RAGShield-SAD-v1.0  
> **文档状态**: 已冻结  
> **创建日期**: 2026-04-28  
> **目标读者**: 三人开发团队、比赛评委、技术审阅者  
> **用途**: 定义 RAGShield 的完整技术架构，指导代码实现和模块划分。

---

## 一、文档控制

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0 | 2026-04-28 | 团队 | 初始版本，覆盖逻辑架构、数据流、模块划分、部署视图 |

---

## 二、设计原则

RAGShield 架构遵循以下核心设计原则：

| 原则 | 说明 | 实践方式 |
|------|------|---------|
| **纵深防御** | 不在单点做检测，而是知识库→检索→生成全链路层层把关 | 三层独立检测模块，每层可独立运行和测试 |
| **可解释性** | 每次检测都输出明确的理由和分数 | 每层返回 risk_score + reason + latency_ms |
| **可降级** | 任一组件故障不影响核心功能 | 每个模型都有 fallback，Docker 镜像预装所有资源 |
| **前后端解耦** | 前端纯展示，后端承载全部业务逻辑 | FastAPI 提供 REST API，Gradio 仅通过 HTTP 调用 |
| **嵌入式部署** | 零运维，单容器跑通全流程 | ChromaDB 嵌入式模式，无需独立数据库服务 |

---

## 三、逻辑架构

### 3.1 总体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           用户/评委                                  │
│                    (浏览器 / curl / 其他 RAG 系统)                    │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ HTTP
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          API 网关层 (FastAPI)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ POST /kb/   │  │ POST /query │  │ GET  /kb/   │  │ GET /health│  │
│  │ upload      │  │             │  │ scan        │  │            │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘  │
│         │                │                │               │         │
│         ▼                ▼                ▼               ▼         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Pydantic 请求/响应校验层                      │  │
│  └───────────────────────┬───────────────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
                           ▼ 内部函数调用
┌─────────────────────────────────────────────────────────────────────┐
│                        检测引擎层 (核心)                               │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │   Layer 1        │  │   Layer 2        │  │   Layer 3        │   │
│  │   知识库层        │  │   检索层         │  │   生成层         │   │
│  │                  │  │                  │  │                  │   │
│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │   │
│  │  │ 离群检测    │  │  │  │ 注意力方差  │  │  │  │ NLI 双路融合│  │   │
│  │  │ IF + LOF   │  │  │  │ 分析        │  │  │  │ reranker   │  │   │
│  │  │ 余弦基线规则│  │  │  │ 注意力熵    │  │  │  │ + chinanli │  │   │
│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │   │
│  │  ┌────────────┐  │  │                  │  │  ┌────────────┐  │   │
│  │  │ 敏感实体    │  │  │                  │  │  │ 生成内容    │  │   │
│  │  │ 正则 + NER  │  │  │                  │  │  │ 审计(预留)  │  │   │
│  │  └────────────┘  │  │                  │  │  └────────────┘  │   │
│  │                  │  │                  │  │                  │   │
│  │  risk_score_1    │  │  risk_score_2    │  │  risk_score_3    │   │
│  │  latency_1       │  │  latency_2       │  │  latency_3       │   │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │
│           │                     │                     │              │
│           └─────────────────────┼─────────────────────┘              │
│                                 ▼                                    │
│                    ┌─────────────────────┐                           │
│                    │   风险融合模块       │                           │
│                    │   weighted_fusion() │                           │
│                    │   0.3*L1+0.3*L2+0.4*L3                         │
│                    └──────────┬──────────┘                           │
│                               ▼                                      │
│                    ┌─────────────────────┐                           │
│                    │   响应决策模块       │                           │
│                    │   safe/warning/danger│                           │
│                    └─────────────────────┘                           │
└─────────────────────────────────────────────────────────────────────┘
                           │
                           ▼ 模型调用
┌─────────────────────────────────────────────────────────────────────┐
│                        模型服务层                                      │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  BAAI/bge-m3    │  │ BAAI/bge-       │  │ uer/roberta-base-   │  │
│  │  (GPU 版主模型)  │  │ reranker-large  │  │ finetuned-chinanli  │  │
│  │  1024维嵌入      │  │ 相似度评分 0~1  │  │ 三分类 NLI          │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ BAAI/bge-small- │  │ HanLP NER       │  │ Kimi API / Qwen2.5  │  │
│  │ zh-v1.5         │  │ (CPU fallback)  │  │ (LLM 生成)          │  │
│  │ (CPU 降级模型)   │  │                 │  │                     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        数据存储层                                      │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              ChromaDB 嵌入式模式 (PersistentClient)              │  │
│  │              本地文件持久化，零运维，单容器                       │  │
│  │              collections: ragshield_kb                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 模块职责矩阵

| 模块 | 职责 | 输入 | 输出 | 负责人 |
|------|------|------|------|--------|
| `api/main.py` | FastAPI 应用入口，路由注册 | — | Swagger UI + REST API | 工程位 |
| `api/schemas.py` | Pydantic 请求/响应模型 | — | 类型安全的 API 契约 | 工程位 |
| `core/embedder.py` | BGE-M3/bge-small 封装，统一嵌入接口 | 文本/文档列表 | 1024/512 维向量 | 算法位 |
| `core/vector_store.py` | ChromaDB 嵌入式封装，抽象存储接口 | 文档向量/查询向量 | 检索结果/存储确认 | 工程位 |
| `layer1_kb/outlier_detector.py` | IF + LOF + 余弦基线规则，离群检测 | 文档嵌入矩阵 | 可疑文档列表 + 分数 | 算法位 |
| `layer1_kb/sensitive_ner.py` | 正则第一层 + HanLP 第二层，敏感实体 | 文档文本 | 实体列表 + 类型 | 算法位 |
| `layer1_kb/context_pollution_detector.py` | 多文档主题一致性（V1 预留接口） | 文档群嵌入 | 可疑标记（V1 占位） | 算法位 |
| `layer1_kb/bias_detector.py` | 情感极性检测（V1 预留接口） | 文档文本 | 偏见标记（V1 占位） | 算法位 |
| `layer2_retrieval/attention_analyzer.py` | 注意力权重计算、方差和熵分析 | 查询向量 + 文档向量 | 方差值 + 熵值 + 是否异常 | 算法位 |
| `layer2_retrieval/relevance_scorer.py` | 查询-文档余弦相似度计算 | 查询向量 + 文档向量 | 相似度分数列表 | 算法位 |
| `layer2_retrieval/diversity_monitor.py` | 检索结果多样性监控（V1 预留） | 检索结果向量 | 多样性分数（V1 占位） | 算法位 |
| `layer3_generation/consistency_checker.py` | bge-reranker + uer/chinanli 双路融合 | 检索内容 + 生成内容 | 一致性判定 + 置信度 | 架构位 |
| `layer3_generation/llm_client.py` | Kimi API / Qwen2.5 封装，统一 LLM 接口 | 查询 + 检索结果 | 生成文本 | 架构位 |
| `layer3_generation/bias_checker.py` | 生成内容中立性检测（V1 预留接口） | 生成文本 | 中立性标记（V1 占位） | 架构位 |
| `fusion/risk_fusion.py` | 三层风险加权融合 | 三层 risk_score | 最终 risk_score + 判定 | 工程位 |
| `frontend/app.py` | Gradio 界面，纯 HTTP 调用 FastAPI | 用户输入 | 可视化展示 | 架构位 |

---

## 四、数据流设计

### 4.1 知识库上传数据流

```
用户上传文档 (JSON/TXT/Markdown)
    │
    ▼
┌─────────────────┐
│ POST /kb/upload │
│ 解析文档格式    │
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│ core.embedder.embed() │  ← BGE-M3 / bge-small
│ 文档 → 向量          │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────────┐
│ core.vector_store.insert()│  ← ChromaDB PersistentClient
│ 向量 + 元数据 → 存储     │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ layer1_kb.outlier_detector.detect()   │  ← IF + LOF + 余弦基线
│ 全量文档嵌入 → 离群检测              │
└────────┬─────────────────────────────┘
         │
         ├──→ 发现可疑文档 → 返回标红列表
         │
         └──→ 正常文档 → 静默完成
```

### 4.2 查询处理数据流（全链路）

```
用户输入查询
    │
    ▼
┌─────────────────────────────┐
│ POST /api/v1/query          │
│ {query, kb_id, top_k=5}     │
└─────────────┬───────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│ Step 0: 嵌入查询                      │
│ core.embedder.embed(query)            │
│ 查询文本 → 查询向量                   │
└──────────────┬───────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│ Layer1 │ │ Layer2 │ │ Layer3 │
│ (并行) │ │ (检索) │ │ (生成) │
└───┬────┘ └───┬────┘ └───┬────┘
    │          │          │
    ▼          ▼          ▼
  知识库层   检索过程    生成验证
  风险评分   风险评分    风险评分
    │          │          │
    └──────────┼──────────┘
               ▼
    ┌──────────────────────┐
    │ fusion.risk_fusion()  │
    │ 0.3*L1 + 0.3*L2 + 0.4*L3
    │ 最终风险评分 + 安全判定 │
    └──────────┬───────────┘
               ▼
    ┌──────────────────────┐
    │ 响应决策              │
    │ safe / warning / danger│
    │ + 三层详情 + 延迟    │
    └──────────┬───────────┘
               ▼
         返回 JSON 响应
```

### 4.3 Layer 1 内部数据流（知识库上传时触发）

```
文档嵌入矩阵 (N x 1024)
    │
    ├──→ Isolation Forest ──→ iso_labels (N x 1)
    │                           iso_scores (N x 1)
    │
    ├──→ LOF ───────────────→ lof_labels (N x 1)
    │                           lof_scores (N x 1)
    │
    └──→ 余弦基线规则 ──────→ cosine_flags (N x 1)
                                avg_similarities (N x 1)
                                │
                                ▼
                    ┌─────────────────────┐
                    │ 综合判定              │
                    │ (iso==-1 && lof==-1) │
                    │   OR cosine_flag     │
                    │ → suspicious_docs    │
                    └─────────────────────┘
```

### 4.4 Layer 3 内部数据流（双路 NLI 融合）

```
检索内容 (premise) + 生成内容 (hypothesis)
    │
    ├──→ bge-reranker ──────→ similarity_score (0~1)
    │
    └──→ uer/chinanli ──────→ nli_label
                                (entailment/contradiction/neutral)
                                │
                                ▼
                    ┌─────────────────────────────┐
                    │ 双路融合判定                   │
                    │                             │
                    │ similarity < 0.3            │
                    │ AND nli == "contradiction"  │
                    │ → high_confidence_block     │
                    │                             │
                    │ similarity < 0.3            │
                    │ OR  nli == "contradiction"  │
                    │ → alert_review              │
                    │                             │
                    │ similarity > 0.7            │
                    │ AND nli == "entailment"     │
                    │ → safe                      │
                    │                             │
                    │ else → neutral              │
                    └─────────────────────────────┘
```

---

## 五、目录结构

```
RAGShield/
├── README.md                          # 项目说明 + 快速开始
├── requirements.txt                   # 生产依赖
├── requirements-dev.txt               # 开发依赖
├── .env.example                       # 环境变量模板
├── Dockerfile                         # Docker 构建文件
├── docker-compose.yml                 # Docker Compose 配置
├── .dockerignore                      # Docker 忽略文件
├── .gitignore                         # Git 忽略文件
├── config/
│   ├── gpu_config.yaml                # GPU 高性能版配置
│   └── cpu_config.yaml                # CPU 轻量化版配置
│
├── src/                               # 核心源码
│   ├── __init__.py
│   │
│   ├── core/                          # 核心基础设施
│   │   ├── __init__.py
│   │   ├── embedder.py               # BGE-M3 / bge-small 统一封装
│   │   ├── vector_store.py           # ChromaDB 嵌入式封装
│   │   └── config.py                 # 配置加载（Pydantic-Settings）
│   │
│   ├── layer1_kb/                     # 知识库层（预防性检测）
│   │   ├── __init__.py
│   │   ├── outlier_detector.py       # IF + LOF + 余弦基线
│   │   ├── sensitive_ner.py          # 正则 + HanLP 分层 NER
│   │   ├── context_pollution_detector.py  # S3 预留接口（V1 占位）
│   │   └── bias_detector.py          # S4 预留接口（V1 占位）
│   │
│   ├── layer2_retrieval/              # 检索层（过程监控）
│   │   ├── __init__.py
│   │   ├── attention_analyzer.py     # 注意力方差 + 熵分析
│   │   ├── relevance_scorer.py       # 查询-文档相似度
│   │   └── diversity_monitor.py      # 多样性监控（V1 预留）
│   │
│   ├── layer3_generation/             # 生成层（输出验证）
│   │   ├── __init__.py
│   │   ├── consistency_checker.py    # bge-reranker + uer/chinanli 双路融合
│   │   ├── llm_client.py            # Kimi API / Qwen2.5 统一封装
│   │   └── bias_checker.py          # 生成中立性检测（V1 预留）
│   │
│   ├── fusion/                        # 风险融合
│   │   ├── __init__.py
│   │   └── risk_fusion.py            # 三层加权融合
│   │
│   ├── api/                           # FastAPI 服务
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 应用入口
│   │   ├── routers/
│   │   │   ├── kb.py               # 知识库路由 (/kb/*)
│   │   │   └── query.py            # 查询路由 (/query)
│   │   └── schemas.py              # Pydantic 请求/响应模型
│   │
│   └── frontend/                      # Gradio 演示界面
│       └── app.py                    # 纯界面层，HTTP 调用 FastAPI
│
├── tests/                             # 测试
│   ├── __init__.py
│   ├── test_layer1.py                # Layer1 单元测试
│   ├── test_layer2.py                # Layer2 单元测试
│   ├── test_layer3.py                # Layer3 单元测试
│   ├── test_fusion.py               # 融合模块测试
│   ├── test_api.py                  # API 集成测试
│   └── conftest.py                  # pytest 共享 fixture
│
├── data/                              # 数据
│   ├── attack_kb/                    # 攻击模板库
│   ├── normal_kb/                    # 正常文档库
│   ├── queries/                      # 查询集合
│   └── chroma_db/                    # ChromaDB 持久化数据（.gitignore）
│
├── scripts/                           # 工具脚本
│   ├── seed_data.py                  # 一键导入测试数据
│   ├── threshold_sweep.py            # 阈值扫描（找最优参数）
│   ├── weight_ablation.py           # 权重消融实验
│   ├── evaluate.py                  # 评测主脚本
│   └── setup.sh                     # 环境初始化脚本
│
├── docs/                              # 项目文档
│   ├── 01_PRD.md
│   ├── 02_Technical_Selection_Report.md
│   ├── 03_Attack_KB_and_Defense_Mapping.md
│   ├── 04_System_Architecture_Design.md
│   ├── 05_API_Contract.md
│   └── reference/
│       └── 01_OpenSource_Projects_and_Benchmarks.md
│
└── notebooks/                         # 实验记录
    └── experiments/                  # 评测结果、图表
```

---

## 六、部署架构

### 6.1 开发环境

```
开发者笔记本
    │
    ├── Conda 虚拟环境 (Python 3.10)
    ├── ChromaDB 嵌入式 (./data/chroma_db/)
    ├── 模型缓存 (~/.cache/huggingface/)
    └── 本地运行: uvicorn src.api.main:app --reload
```

### 6.2 生产/比赛环境

```
单容器部署 (Docker)
    │
    ┌─────────────────────────────────────┐
    │  ragshield-api 容器                  │
    │                                     │
    │  ┌──────────────┐                  │
    │  │  FastAPI     │  ← 业务核心      │
    │  │  (port 8000) │                  │
    │  └──────┬───────┘                  │
    │         │                          │
    │  ┌──────┴───────┐                  │
    │  │  Gradio      │  ← 纯界面层      │
    │  │  (port 7860) │    HTTP→FastAPI  │
    │  └──────────────┘                  │
    │                                     │
    │  ┌──────────────┐                  │
    │  │ ChromaDB      │  ← 嵌入式模式   │
    │  │ (./chroma_db)│    本地文件     │
    │  └──────────────┘                  │
    │                                     │
    │  预装模型:                           │
    │  - BGE-M3 / bge-small-zh            │
    │  - bge-reranker                     │
    │  - uer/chinanli                     │
    │  - HanLP                            │
    │  - Qwen2.5 (INT4, optional)         │
    └─────────────────────────────────────┘
```

### 6.3 Dockerfile 要点

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 预下载模型（构建时完成，运行时零下载）
COPY scripts/download_models.py .
RUN python download_models.py

# 复制源码
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# 环境变量
ENV PYTHONPATH=/app
ENV CONFIG_PATH=/app/config/gpu_config.yaml

# 暴露端口
EXPOSE 8000 7860

# 启动: FastAPI + Gradio
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 七、关键架构决策记录

### ADR-005：为什么每个 Layer 预留 V1 占位接口？

**背景**：S3（上下文污染）和 S4（偏见引导）的完整实现算法复杂度高，三人团队 V1 难以完成。

**决策**：为 S3/S4 检测模块预留接口文件，V1 返回占位结果，架构上展示扩展性。

**实现方式**：
- `layer1_kb/context_pollution_detector.py`：存在但 V1 直接返回 `{"detected": false, "confidence": 0.0}`
- `layer1_kb/bias_detector.py`：存在但 V1 直接返回占位
- 答辩时说"架构已预留 S3/S4 检测模块，V2 迭代实现完整逻辑"

### ADR-006：为什么融合模块用固定权重而非动态权重？

**背景**：动态权重（根据场景自适应调整）效果更好，但实现复杂。

**决策**：V1 用固定权重（0.3/0.3/0.4），V2 探索动态权重。

**理由**：
1. 固定权重已有消融实验数据支撑
2. 动态权重需要更大的训练数据量，三人团队 V1 不具备条件
3. 固定权重可解释性更强，答辩时更容易讲清楚

### ADR-007：为什么模型预下载而非运行时下载？

**背景**：HuggingFace 模型通常运行时自动下载，但比赛现场网络不稳定。

**决策**：Docker 构建时预下载所有模型，运行时零网络依赖。

**实现方式**：
- `scripts/download_models.py` 在 Docker build 阶段执行
- 模型缓存到容器内 `/root/.cache/huggingface/`
- 现场 `docker load < ragshield.tar` 后，所有模型已就绪

---

*文档版本: v1.0 | 状态: 已冻结 | 下次评审: Week 3 对齐会*
