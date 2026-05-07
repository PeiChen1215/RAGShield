# RAGShield 技术选型报告

> **文档标识**: RAGShield-TSR-v1.0  
> **文档状态**: 草案 → 评审中 → 已冻结  
> **创建日期**: 2026-04-28  
> **目标读者**: 三人开发团队、比赛评委、技术审阅者  
> **撰写原则**: 每个技术决策必须有"候选方案→对比维度→选择理由→回退方案"的完整论证链。
>
> **竞赛适配定位**：本报告为三人学生团队参加网络技术挑战赛 A&T 赛道量身定制。所有选型遵循"成熟低风险 + 中文优先 + 可降级"原则：主路径采用开箱即用的开源方案确保开发效率，每条决策都配有 fallback 链和量化模型，确保比赛现场任何环境下都能流畅演示。

---

## 一、文档控制

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v0.1 | 2026-04-28 | 团队 | 初始版本，覆盖全部技术栈选型 |
| v1.0 | — | — | Week 1 对齐会后冻结 |

---

## 二、技术栈总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAGShield 技术架构                            │
├─────────────────────────────────────────────────────────────────────┤
│  前端界面层     │  Gradio (纯界面) ──HTTP──→ FastAPI               │
├─────────────────────────────────────────────────────────────────────┤
│  API 业务层     │  FastAPI + Uvicorn + Pydantic (100% 业务逻辑)     │
├─────────────────────────────────────────────────────────────────────┤
│  检测引擎层     │  Layer1: 离群检测 (IF + LOF + 余弦基线规则)        │
│               │  Layer2: 注意力分析 (注意力方差 + 熵值)              │
│               │  Layer3: 一致性验证 (bge-reranker + uer/chinanli) │
├─────────────────────────────────────────────────────────────────────┤
│  模型服务层     │  BGE-M3/bge-small (嵌入) + bge-reranker (相似度)  │
│               │  uer/chinanli (NLI 三分类) + Kimi API (生成 LLM)  │
├─────────────────────────────────────────────────────────────────────┤
│  数据存储层     │  ChromaDB 嵌入式 (本地文件/SQLite，零运维)         │
├─────────────────────────────────────────────────────────────────────┤
│  基础设施层     │  Docker Compose (单容器) / Conda / Python 3.10    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、逐项技术选型决策

### 3.1 编程语言与运行时

#### 决策：Python 3.10

| 维度 | 分析 |
|------|------|
| **候选方案** | Python 3.9 / 3.10 / 3.11 / 3.12 |
| **对比维度** | 库兼容性、类型提示成熟度、性能、团队熟悉度 |
| **选择理由** | 3.10 是当前 ML/AI 生态的**最佳平衡点**：兼容 `match-case` 语法；asyncio 成熟；PyTorch/Transformers/scikit-learn 全面支持；比 3.11+ 更稳定，避免未知兼容性问题 |
| **回退方案** | 若特定依赖要求 3.11，可升级至 3.11（兼容风险可控） |
| **版本锁定** | `python = "^3.10,<3.12"` |

**环境管理**：Conda + `requirements.txt`
- 不用 Poetry（团队学习成本高），不用 pipenv（已过时）
- 用 Conda 管理 Python 版本和虚拟环境，用 `requirements.txt` 管理包依赖

---

### 3.2 后端服务框架

#### 决策：FastAPI

| 维度 | 分析 |
|------|------|
| **候选方案** | FastAPI / Flask / Django / Sanic |
| **对比维度** | 异步性能、API 文档自动生成、类型安全、学习曲线、生态成熟度 |

**详细对比矩阵**：

| 框架 | 异步原生 | 自动 API 文档 | 类型校验 | 学习曲线 | RAG/ML 生态 |
|------|---------|-------------|---------|---------|------------|
| **FastAPI** | ✅ Starlette | ✅ Swagger UI | ✅ Pydantic | 中 | 极佳 |
| Flask | ❌ 需扩展 | ❌ 需扩展 | ❌ 手动 | 低 | 好 |
| Django | ❌ 太重 | ❌ DRF | ✅ Serializers | 高 | 一般 |
| Sanic | ✅ | ❌ | ❌ | 中 | 差 |

| **选择理由** | 1. **异步高性能**：检测层涉及 I/O（LLM API 调用）和 CPU（嵌入/NLI），FastAPI 的 async/await 能优雅处理混合负载<br>2. **自动 API 文档**：集成 Swagger UI，比赛现场可直接展示 API 文档页面<br>3. **Pydantic 集成**：请求/响应模型天然支持类型校验，与 Layer 间数据契约完美契合<br>4. **生态对齐**：HuggingFace、LangChain、ChromaDB 官方示例多用 FastAPI |
| **回退方案** | 若 async 调试困难，可降级为 Flask + Flask-RESTX（牺牲性能换取开发速度） |
| **核心依赖** | `fastapi = "^0.115"`, `uvicorn[standard] = "^0.32"`, `pydantic = "^2.9"` |

---

### 3.3 嵌入模型 (Embedding Model)

#### 决策：BAAI/bge-m3

| 维度 | 分析 |
|------|------|
| **候选方案** | BGE-M3 / BCEmbedding (damo/nlp_corom_sentence-embedding_chinese-base) / GTE (Alibaba) / OpenAI text-embedding-3 |
| **对比维度** | 中文效果、多语言支持、向量维度、开源协议、推理速度、RAG 领域引用率 |

**详细对比矩阵**：

| 模型 | 中文效果 | 多语言 | 维度 | 开源 | 推理速度 | RAG 领域引用 |
|------|---------|--------|------|------|---------|-------------|
| **BGE-M3** | ⭐⭐⭐ 最优 | ✅ 中英 100+ | 1024 | ✅ MIT | 中等 | 高（论文标配） |
| BCEmbedding | ⭐⭐⭐ 最优 | ✅ 中英 | 768 | ✅ | 快 | 中 |
| GTE-large | ⭐⭐⭐ 优 | ✅ 多语言 | 1024 | ✅ Apache | 快 | 中 |
| OpenAI text-emb-3 | ⭐⭐ 良 | ✅ 多语言 | 3072 | ❌ 付费 | 依赖 API | 高 |

| **选择理由** | 1. **中文场景专项优化**：BGE-M3 是当前中文 Embedding 的 SOTA，在 C-MTEB 中文评测基准上领先<br>2. **多粒度支持**：支持句子、段落、文档级嵌入，适配不同长度知识库文档<br>3. **论文已引用**：RAGShield 原始 PDF 已引用 BGE-M3，保持一致性<br>4. **本地推理可控**：不依赖外部 API，延迟可控，符合 <150ms 目标<br>5. **1024 维向量**：与主流向量数据库兼容性最佳 |
| **回退方案（GPU→CPU 降级链）** | 若显存不足（BGE-M3 需 ~2GB），按以下优先级降级：<br>1. **INT8 量化**：使用 `optimum` 库对 BGE-M3 做 8-bit 量化，显存降至 ~1GB，精度损失 <2%<br>2. **降级 BGE-small-zh-v1.5**：512 维，速度提升 5-10 倍，显存 ~500MB，精度略降但仍优于多数模型<br>3. **CPU 推理**：无 GPU 时 PyTorch 自动 fallback 到 CPU，延迟升至 ~200-500ms |
| **为什么不双模型并行？** | 不建议检索用 bge-small、检测用 BGE-M3 的"双模型并行"方案。原因：<br>1. **向量空间不可比**：不同模型的向量空间不兼容，同一文档在两个空间下的"邻居"可能完全不同，离群检测结果不可靠<br>2. **架构复杂度翻倍**：需维护两份向量存储、两套索引，开发调试成本陡增<br>3. **更简单可靠的替代**：如需速度优化，在 BGE-M3 方案上优化 `batch_size` + `torch.compile` 即可，无需引入第二模型<br><br>结论：**bge-small-zh 作为整体降级方案（CPU 版主用），而非与 BGE-M3 并行。** |
| **双版本配置策略** | 准备两套模型配置，通过 `config/gpu_config.yaml` 和 `config/cpu_config.yaml` 切换：<br><br>```yaml
# config/gpu_config.yaml —— 高性能版
embedding:
  model: BAAI/bge-m3
  device: cuda
  batch_size: 32
  compile: true  # torch.compile 加速

# config/cpu_config.yaml —— 轻量化版
embedding:
  model: BAAI/bge-small-zh-v1.5
  device: cpu
  batch_size: 8
  compile: false
``` |
| **核心依赖** | `sentence-transformers = "^3.0"`, `torch = "^2.3"` |
| **加载方式** | 本地缓存：`sentence-transformers` 自动下载到 `~/.cache/`；比赛环境提前下载打包 |

---

### 3.4 向量数据库

#### 决策：ChromaDB（主）+ pgvector（预留扩展）

| 维度 | 分析 |
|------|------|
| **候选方案** | ChromaDB / Milvus / pgvector / FAISS / Qdrant / Weaviate |
| **对比维度** | 部署复杂度、查询性能、持久化、客户端生态、Python 集成、向量维度支持 |

**详细对比矩阵**：

| 数据库 | 部署难度 | 查询性能 | 持久化 | Python 集成 | 维度限制 | 团队熟悉度 |
|--------|---------|---------|--------|------------|---------|-----------|
| **ChromaDB** | ⭐ 极低（pip install） | 中等 | ✅ SQLite/文件 | ⭐ 原生 Python | 无限制 | 低（易上手） |
| Milvus | 高（需 Docker/K8s） | ⭐ 极高 | ✅ | 好 | 无限制 | 无 |
| **pgvector** | 低（PostgreSQL 扩展） | 中等 | ✅ ACID | 好（psycopg2） | 16,000 | 中（需 PG 基础） |
| FAISS | 中（仅索引，无持久化） | ⭐ 极高 | ❌ 需自建 | 好 | 无限制 | 无 |
| Qdrant | 中（Docker） | 高 | ✅ | 好 | 无限制 | 无 |

| **选择理由（ChromaDB 嵌入式模式）** | 1. **零运维风险**：采用 `chromadb.PersistentClient(path="./chroma_db")` 嵌入式模式，**无需启动独立服务**，直接在 Python 进程内运行，基于本地 SQLite/文件持久化<br>2. **单容器部署**：Docker 内仅需一个 `ragshield-api` 容器，无需额外 ChromaDB 服务容器，避免端口占用、服务通信失败等现场故障<br>3. **零配置上手**：`pip install chromadb` + 一行代码初始化，三人团队无需运维精力<br>4. **生态兼容**：Awesome-Rag-Attacks、Trojan-RAG-Demo 均使用 ChromaDB 嵌入式模式，可直接复用其数据格式<br>5. **比赛现场保障**：文件型持久化更容易备份和迁移，提前构建 Docker 镜像时数据库文件已预置 |
| **pgvector 的定位** | 仅在技术文档中作为「生产环境扩展方案」提及，V1.0 **不实现**。理由：<br>1. PostgreSQL 运维超出三人团队当前能力范围<br>2. 比赛中无需展示多后端切换能力，聚焦核心防御效果<br>3. 架构中通过 `VectorStore` 抽象接口预留扩展点，V2 可无缝接入 |
| **回退方案** | 若 ChromaDB 嵌入式模式性能不足（>1000 文档时），可切换到 FAISS（内存索引）或 Milvus Lite（轻量版） |
| **核心依赖** | `chromadb = "^0.5"` |
| **初始化代码** | ```python
import chromadb
# 嵌入式模式：无需启动服务，本地文件持久化
chroma_client = chromadb.PersistentClient(path="./data/chroma_db")
collection = chroma_client.get_or_create_collection(name="ragshield_kb")
``` |

---

### 3.5 大语言模型 (LLM) 接口

#### 决策：Kimi API (Moonshot) 为主，本地 Qwen2.5-7B 为 fallback

| 维度 | 分析 |
|------|------|
| **候选方案** | Kimi API / DeepSeek API / OpenAI API / 本地 Qwen2.5 / 本地 LLaMA-3 |
| **对比维度** | 中文效果、API 稳定性、成本、延迟、可用性（会员 vs API）、本地部署难度 |

**详细对比矩阵**：

| 方案 | 中文效果 | 稳定性 | 成本 | 延迟 | 可用性 | 本地部署 |
|------|---------|--------|------|------|--------|---------|
| **Kimi API** | ⭐ 极佳 | 高 | 中（有免费额度） | 网络依赖 | ⭐ 已有会员，API Key 需另申请 | ❌ |
| DeepSeek API | ⭐ 极佳 | 高 | 低 | 网络依赖 | 需注册申请 | ❌ |
| OpenAI API | 良 | 中（国内不稳定） | 高 | 网络依赖 | 需海外支付 | ❌ |
| **本地 Qwen2.5-7B** | ⭐ 极佳 | ⭐ 本地可控 | 无 | ⭐ 本地 <100ms | ⭐ 随时可用 | ✅ 需 ~15GB 显存 |
| 本地 LLaMA-3-8B | 良 | 可控 | 无 | 本地 | 随时可用 | ✅ 需 ~8GB 显存 |

| **选择理由（Kimi API）** | 1. **团队已有资源**：99 元/月会员可搭配 API Key 使用（需在 Moonshot AI 开放平台单独申请 API Key，与会员独立）<br>2. **中文长文本能力强**：支持 200K 上下文，对长文档检索场景友好<br>3. **API 格式兼容**：采用 OpenAI SDK 格式（`openai-python` 库可直接调用），降低集成成本 |
| **fallback 策略（本地 Qwen2.5）** | 1. **高可用保障**：比赛现场网络不稳定时，本地模型确保演示不中断<br>2. **延迟保障**：本地推理延迟可控，不受网络波动影响<br>3. **资源评估**：Qwen2.5-7B-Instruct INT4 量化后约需 8GB 显存，RTX 4060/3060 可运行；若无 GPU，CPU 推理延迟约 5-10s/请求（仅作 backup）<br>4. **定位**：Layer3 的 NLI 判断不走 LLM API，用本地轻量模型；Kimi API 仅用于"生成回答"环节 |
| **离线镜像策略** | 比赛现场可能无网络或网络不稳定，需提前将 Qwen2.5-7B INT4 模型下载到本地，打包进 Docker 镜像。模型文件通过 HuggingFace 镜像站（如 hf-mirror.com）提前下载，避免现场下载失败。<br>`docker save ragshield:latest > ragshield.tar`，现场 `docker load < ragshield.tar` 一键恢复。 |
| **成本估算** | Kimi API `moonshot-v1-8k` 模型：约 0.006 元/1K tokens；单次查询（检索结果 + 生成）约 2K tokens → **单次成本 ~0.012 元**。比赛演示 100 次约 1.2 元。 |
| **核心依赖** | `openai = "^1.50"`（Kimi API 兼容 OpenAI SDK 格式） |
| **环境变量** | `KIMI_API_KEY=sk-...`, `KIMI_BASE_URL=https://api.moonshot.cn/v1` |

> ⚠️ **重要提醒**：Kimi 99 元会员是**网页聊天会员**，与 API Key 是**两套体系**。需要在 https://platform.moonshot.cn/ 单独注册开发者账号并申请 API Key，有免费额度（通常 15 元）。

---

### 3.6 NLI 模型（自然语言推理）

#### 决策：本地 bge-reranker-large 为主 + uer/chinanli 为辅的双路融合

| 维度 | 分析 |
|------|------|
| **候选方案** | bge-reranker / uer/roberta-base-finetuned-chinanli-chinese / cross-encoder/ms-marco-MiniLM-L-6-v2 / 走 LLM API 做 NLI / 本地 RoBERTa 微调 |
| **对比维度** | 准确性、推理速度、中文支持、是否依赖外部 API、模型大小、矛盾检测召回率 |

**详细对比矩阵**：

| 方案 | 相似度判别 | 矛盾检测召回 | 中文支持 | 推理速度 | 外部依赖 | 模型大小 |
|------|-----------|-------------|---------|---------|---------|---------|
| **bge-reranker** | ⭐ 高 | 中（非专门 NLI） | ⭐ 原生 | 快（本地） | ❌ 无 | ~1GB |
| **uer/chinanli** | ❌ 无（三分类） | ⭐ 高（专门 NLI） | ⭐ 原生 | 快（本地） | ❌ 无 | **~110MB** |
| cross-encoder MiniLM | 中 | 中 | 需适配 | 快 | ❌ 无 | ~100MB |
| LLM API (Kimi) | ⭐ 高 | ⭐ 高 | ⭐ 好 | 慢（网络） | ✅ 依赖 API | — |

| **选择理由（双路融合）** | 1. **bge-reranker 负责语义相似度评分**：输出 0-1 的连续分数，可解释性强，便于融合到风险评分体系<br>2. **uer/chinanli 负责矛盾判定**：专门做 entailment/contradiction/neutral 三分类，对"矛盾"的召回率显著高于 reranker<br>3. **双路互补**：reranker 擅长"支持"判断（高分即支持），chinanli 擅长"矛盾"判断（低分不一定是矛盾，但 contradiction 标签是明确信号）<br>4. **轻量可运行**：uer/chinanli 仅 110MB，CPU 推理 <20ms，不增加架构负担 |
| **融合判定策略（双路交叉验证）** | 采用双模型联合决策，提升召回率、降低误报：<br><br>```python
# 双路融合逻辑
reranker_score = bge_reranker(similarity, premise, hypothesis)  # 0~1
nli_label = uer_chinanli(premise, hypothesis)  # entailment|neutral|contradiction

if reranker_score < 0.3 and nli_label == "contradiction":
    # 双模型一致判定为矛盾 → 高置信度阻断
    return "high_confidence_block"
elif reranker_score < 0.3 or nli_label == "contradiction":
    # 单一模型触发 → 告警 + 人工复核
    return "alert_review"
elif reranker_score > 0.7 and nli_label == "entailment":
    # 双模型一致支持 → 安全通过
    return "safe"
else:
    return "neutral"
```<br><br>**答辩话术**："我们采用 bge-reranker + 中文 NLI 的双路交叉验证机制，reranker 负责语义相似度量化评分，专门 NLI 模型负责矛盾/支持三分类。仅当双模型一致判定 contradiction 时，才执行高置信度阻断；单一模型触发时，降为告警+人工复核。这一设计在极小代码开销下（~15 行），显著提升了 Layer3 的检测准确率和可解释性。" |
| **核心依赖** | `sentence-transformers = "^3.0"`, `transformers = "^4.45"` |
| **模型加载** | ```python
from sentence_transformers import CrossEncoder
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# bge-reranker
reranker = CrossEncoder("BAAI/bge-reranker-large")

# uer/chinanli
nli_tokenizer = AutoTokenizer.from_pretrained("uer/roberta-base-finetuned-chinanli-chinese")
nli_model = AutoModelForSequenceClassification.from_pretrained("uer/roberta-base-finetuned-chinanli-chinese")
``` |

---

### 3.7 离群检测算法

#### 决策：Isolation Forest + LOF（局部离群因子）双模型融合

| 维度 | 分析 |
|------|------|
| **候选方案** | Isolation Forest / LOF / One-Class SVM / DBSCAN / 基于统计的 Z-Score |
| **对比维度** | 对高维向量适应性、异常判定可解释性、训练是否需要标签、对簇状异常敏感度 |

**详细对比矩阵**：

| 算法 | 高维适应 | 无监督 | 可解释性 | 对簇状异常 | 计算速度 |
|------|---------|--------|---------|-----------|---------|
| **Isolation Forest** | ⭐ 好 | ✅ | 中（路径长度） | 弱（单点） | ⭐ 快 |
| **LOF** | 好 | ✅ | 中（局部密度比） | ⭐ 强 | 中等 |
| One-Class SVM | 差 | ✅ | 差 | 弱 | 慢 |
| DBSCAN | 差 | ✅ | 差（聚类） | ⭐ 强 | 中等 |
| Z-Score | 差 | ✅ | ⭐ 强 | 弱 | ⭐ 快 |

| **选择理由（IF + LOF 融合）** | 1. **互补性**：Isolation Forest 擅长发现**全局离群点**（孤立文档），LOF 擅长发现**局部密度异常**（小簇恶意文档群）<br>2. **无监督**：无需标注数据，适合比赛场景快速启动<br>3. **可解释**：IF 的异常分数基于路径长度，LOF 基于局部密度比，融合后分数有明确数学含义<br>4. **PDF 已论证**：原始文档中已提供伪代码，团队对该方案有认知基础 |
| **融合策略** | 双算法均判定为异常（`iso_label == -1` 且 `lof_label == -1`）才标记为可疑，降低误报 |
| **规则兜底：余弦相似度基线（小知识库场景）** | 比赛演示通常只用 50~100 篇文档，无监督算法在小样本下极易不稳定（误报高）。补充极简规则兜底：<br><br>```python
def cosine_baseline_outlier(doc_embedding, all_embeddings, threshold=0.4):
    """计算单篇文档与知识库全量文档的平均余弦相似度，低于阈值标记为离群"""
    similarities = cosine_similarity([doc_embedding], all_embeddings)[0]
    avg_sim = np.mean(similarities)
    return avg_sim < threshold, avg_sim

# 最终判定：无监督算法 OR 规则兜底任一触发即告警
is_suspicious = (if_label == -1 and lof_label == -1) or cosine_flag
```<br><br>**优势**：<br>1. 小知识库下极其稳定，不受样本量影响<br>2. 计算量极小（一次矩阵乘法），延迟 <1ms<br>3. 与 IF+LOF 做 OR 逻辑，演示场景下效果有保障 |
| **核心依赖** | `scikit-learn = "^1.5"`, `numpy` |

---

### 3.8 中文命名实体识别 (NER)

#### 决策：HanLP（轻量） + 正则规则 混合策略

| 维度 | 分析 |
|------|------|
| **候选方案** | HanLP / Jieba + 自定义词典 / LTP / paddlenlp / 微调的 BERT-CRF |
| **对比维度** | 中文实体准确率、安装复杂度、模型大小、推理速度、可定制性 |

**详细对比矩阵**：

| 方案 | 准确率 | 安装 | 模型大小 | 速度 | 定制性 |
|------|--------|------|---------|------|--------|
| **HanLP** | ⭐ 高 | pip 一键 | ~100MB | 快 | ⭐ 强 |
| Jieba | 中 | pip 一键 | 无 | ⭐ 快 | 强（词典） |
| LTP | 高 | 复杂 | ~400MB | 中等 | 弱 |
| paddlenlp | 高 | 复杂 | ~1GB | 中等 | 中 |
| 微调 BERT-CRF | ⭐ 最高 | 需训练 | ~400MB | 慢 | 需数据 |

| **选择理由（HanLP + 正则分层检测）** | 采用分层处理策略，正则先行、NER 兜底，兼顾速度与准确率：<br><br>**第一层：正则规则（结构化敏感信息，速度极快）**<br>```python
import re

# 身份证号、手机号、邮箱、银行卡号——正则准确率 100%
RULES = {
    "id_card": r"\d{17}[\dXx]|\d{15}",
    "mobile": r"1[3-9]\d{9}",
    "email": r"[\w.-]+@[\w.-]+\.\w+",
    "bank_card": r"\d{16,19}",
    "api_key": r"(sk-|ak-)[a-zA-Z0-9]{20,}",
}
```<br>**第二层：HanLP NER（非结构化实体，模型兜底）**<br>```python
import hanlp
# 仅对正则未命中的内容运行 NER
ner = hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)
```<br><br>**处理流程**：<br>1. 先用正则扫描文档全文，命中即返回（<1ms）<br>2. 正则未覆盖的内容，送入 HanLP NER 检测人名、机构名、地名（~10ms）<br>3. 合并两层结果输出<br><br>**优势**：<br>- 结构化信息（身份证、手机号等）由正则 100% 准确捕获，无需模型<br>- NER 模型只处理需要语义理解的部分，算力消耗降低 50%+<br>- 整体检测延迟 <15ms/文档 | 
| **回退方案** | 若 HanLP 依赖冲突，降级为 `jieba` + 自定义敏感词词典 + 正则规则 |
| **核心依赖** | `hanlp = "^2.1"`（或 `jieba = "^0.42"`） |

---

### 3.9 前端演示界面

#### 决策：Gradio

| 维度 | 分析 |
|------|------|
| **候选方案** | Gradio / Streamlit / React + FastAPI / 纯 CLI |
| **对比维度** | 开发速度、可视化能力、与 FastAPI 集成、组件丰富度、部署复杂度 |

**详细对比矩阵**：

| 方案 | 开发速度 | 可视化 | API 集成 | 组件 | 部署 |
|------|---------|--------|---------|------|------|
| **Gradio** | ⭐ 极快 | 良好 | 好（可嵌入 FastAPI） | 丰富 | 简单 |
| Streamlit | ⭐ 极快 | 良好 | 一般 | 丰富 | 简单 |
| React | 慢 | ⭐ 极佳 | 需自建 | 极丰富 | 复杂 |
| CLI | 快 | ❌ 无 | 直接 | 无 | 极简 |

| **选择理由（Gradio + FastAPI 完全解耦）** | 严格遵循**"FastAPI 承载 100% 业务逻辑，Gradio 仅做界面层通过 HTTP 调用 FastAPI"** 的开发模式：<br><br>```
┌─────────────┐      HTTP POST      ┌─────────────┐
│   Gradio    │  ───────────────→  │   FastAPI   │
│  (纯界面层)  │    /api/v1/query    │  (业务核心)  │
│             │  ←───────────────  │             │
└─────────────┘    返回 risk_score   └─────────────┘
```<br><br>**优势 1——答辩说服力**：可同时展示可视化 Web 界面（Gradio）和 Swagger API 文档（FastAPI 自动生成）。评委问及"能否对接企业现有 RAG 系统"时，直接给出 `curl` 命令，证明项目的可集成性。<br><br>**优势 2——现场安全**：界面与业务逻辑完全解耦，修改演示界面不会影响核心检测逻辑，避免现场调试时误改核心代码导致翻车。<br><br>**优势 3——开发效率**：Gradio `gr.Plot()` 可直接展示 Matplotlib 图表（注意力分布、嵌入空间 TSNE 图），15 分钟出界面，无专职前端时最优解。<br><br>**Gradio 调用 FastAPI 示例**：<br>```python
# frontend/app.py —— Gradio 界面，纯调用层
import gradio as gr
import httpx

API_BASE = "http://localhost:8000/api/v1"

def on_query_submit(query, kb_id):
    """Gradio 按钮回调——仅做 HTTP 调用，零业务逻辑"""
    resp = httpx.post(f"{API_BASE}/query", json={"query": query, "kb_id": kb_id})
    result = resp.json()
    return (
        result["answer"],
        f"风险评分: {result['final_risk_score']:.2f}",
        result["is_safe"],
        result["details"],
    )

# Gradio 界面定义（纯布局代码，不涉及检测逻辑）
with gr.Blocks(title="RAGShield 防御演示") as demo:
    gr.Markdown("# RAGShield 知识库安全检测系统")
    with gr.Row():
        with gr.Column(scale=1):
            query_input = gr.Textbox(label="输入查询")
            submit_btn = gr.Button("提交检测")
        with gr.Column(scale=2):
            risk_gauge = gr.Number(label="风险评分")
            answer_output = gr.Textbox(label="生成结果")
            detail_json = gr.JSON(label="检测详情")
    submit_btn.click(on_query_submit, [query_input], [answer_output, risk_gauge, detail_json])

demo.launch()
``` |
| **回退方案** | 若 Gradio 样式不满足，可切换 Streamlit（更灵活的布局）；若时间充裕，可用纯 React 做更精美界面。无论前端如何变化，FastAPI 接口保持不变。 |
| **核心依赖** | `gradio = "^5.0"`, `httpx = "^0.27"` |

---

### 3.10 容器化与部署

#### 决策：Docker Compose（单节点）

| 维度 | 分析 |
|------|------|
| **候选方案** | Docker Compose / 裸机 Conda / Kubernetes / Serverless |
| **对比维度** | 部署复杂度、环境一致性、团队熟悉度、比赛场景适配 |

| **选择理由（Docker Compose + 单容器）** | 1. **环境一致性**：开发环境、测试环境、比赛现场环境完全一致，"在我电脑上能跑"问题归零<br>2. **单容器部署**：ChromaDB 采用嵌入式模式，**仅需一个容器** `ragshield-api`，无需额外数据库服务，避免端口占用、服务通信失败等现场故障<br>3. **一键启动**：`docker-compose up -d` 拉起即完成部署，30 秒内可交互<br>4. **比赛现场保障**：提前构建好镜像，比赛现场只需 Docker 运行，不受网络环境影响 |
| **服务拆分** | V1 **仅需 1 个服务**：<br>- `ragshield-api`: FastAPI 应用（含所有检测层 + ChromaDB 嵌入式数据库 + Gradio 界面）<br><br>ChromaDB 嵌入式模式在 Python 进程内运行，基于本地文件持久化，无需独立服务容器。 |
| **预构建镜像策略（比赛现场零依赖）** | 1. **Week 4 前完成**：`docker build -t ragshield:latest .` + `docker save ragshield:latest > ragshield_v1.tar`<br>2. **包含所有离线资源**：BGE-M3 / bge-small-zh 模型文件、bge-reranker + uer/chinanli NLI 模型、测试数据集、前端静态文件<br>3. **现场恢复**：`docker load < ragshield_v1.tar && docker-compose up -d`，30 秒启动<br>4. **双镜像准备**：`ragshield-gpu.tar`（含 BGE-M3 完整模型）和 `ragshield-cpu.tar`（含 bge-small 轻量模型），根据现场设备选择 |
| **核心文件** | `Dockerfile`, `docker-compose.yml`, `.dockerignore` |

---

## 四、技术栈总表

| 层级 | 组件 | 技术选型 | 版本 | 用途 |
|------|------|---------|------|------|
| **语言** | Python | Python 3.10 | 3.10.x | 运行时 |
| **环境** | 包管理 | Conda + pip + requirements.txt | — | 虚拟环境 |
| **后端** | Web 框架 | FastAPI | ^0.115 | API 服务 |
| | ASGI 服务器 | Uvicorn[standard] | ^0.32 | HTTP 服务 |
| | 数据校验 | Pydantic | ^2.9 | 请求/响应模型 |
| **前端** | 演示界面 | Gradio | ^5.0 | 可视化 Demo |
| **AI/ML** | 嵌入模型 | BAAI/bge-m3 | — | 文档向量化（GPU 版主模型，1024 维） |
| | 嵌入模型(降级) | BAAI/bge-small-zh-v1.5 | — | 文档向量化（CPU 版降级模型，512 维） |
| | NLI/重排序 | BAAI/bge-reranker-large | — | 语义相似度评分（0~1） |
| | NLI/矛盾检测 | uer/roberta-base-finetuned-chinanli-chinese | — | 三分类：entailment/contradiction/neutral |
| | LLM 生成 | Kimi API (moonshot-v1-8k) | — | 生成回答（在线） |
| | LLM fallback | Qwen2.5-7B-Instruct INT4 (本地) | — | 离线生成（需 ~8GB 显存） |
| | 离群检测 | Isolation Forest + LOF | scikit-learn ^1.5 | Layer1 无监督检测 |
| | 离群检测(规则兜底) | 余弦相似度基线 | numpy | 小知识库场景下稳定兜底 |
| | NER(第一层) | 正则规则 | — | 身份证/手机号/邮箱等结构化信息 |
| | NER(第二层) | HanLP (MSRA_NER_BERT_BASE_ZH) | ^2.1 | 人名/机构名/地名检测 |
| | NER(降级) | jieba + 正则 | ^0.42 | HanLP 冲突时降级 |
| **数据** | 向量数据库 | ChromaDB | ^0.5 | 主存储 |
| | 向量数据库(扩展) | pgvector | — | 生产扩展 |
| **部署** | 容器化 | Docker + Docker Compose | — | 部署打包 |
| **开发** | 格式化 | Black | ^24.0 | 代码风格 |
| | 排序 | isort | ^5.13 | 导入排序 |
| | 检查 | Flake8 | ^7.0 | 静态检查 |
| | 测试 | pytest | ^8.0 | 单元测试 |

---

## 五、requirements.txt 模板

```txt
# ===== RAGShield 核心依赖 =====
# --- 运行时 ---
python-dotenv>=1.0.0
pydantic>=2.9.0
pydantic-settings>=2.5.0

# --- Web 框架 ---
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
gradio>=5.0.0

# --- AI/ML ---
torch>=2.3.0
transformers>=4.45.0
sentence-transformers>=3.0.0
numpy>=1.26.0
scikit-learn>=1.5.0
scipy>=1.13.0

# --- 中文处理 ---
hanlp>=2.1.0
# 若 HanLP 安装失败，回退到: jieba>=0.42.1

# --- 向量数据库 ---
chromadb>=0.5.0
# 扩展: psycopg2-binary>=2.9.0

# --- LLM API ---
openai>=1.50.0

# --- 前端调用 ---
httpx>=0.27.0

# --- 数据/工具 ---
pandas>=2.2.0

# ===== 开发依赖 (requirements-dev.txt) =====
# black>=24.0.0
# isort>=5.13.0
# flake8>=7.0.0
# pytest>=8.0.0
# pytest-asyncio>=0.24.0
```

---

## 六、关键架构决策记录 (ADR)

### ADR-001：为什么不用 LangChain / LlamaIndex 作为 RAG 框架？

**背景**：多个开源项目（Awesome-Rag-Attacks、TrustRAG）使用 LangChain 构建 Victim RAG。

**决策**：RAGShield 不基于 LangChain 构建，而是作为**独立安全中间件**。

**理由**：
1. **定位清晰**：我们是"安全插件"而非"RAG 框架"。用户已有 RAG 系统，RAGShield 只负责安全检测。
2. **避免依赖膨胀**：LangChain 及其依赖体积庞大，增加部署复杂度和冲突风险。
3. **通用性**：通过 FastAPI 接口与任意 RAG 系统对接，不限定用户的 RAG 技术栈。
4. **可复现性**：安全比赛要求代码可控、行为可解释，自研核心流程更易于调试和审计。

**妥协**：评测阶段可写一个小型 LangChain 适配器（`adapters/langchain_adapter.py`）用于演示集成。

---

### ADR-002：为什么 NLI 不走 LLM API，而用本地双路融合模型？

**背景**：Layer3 一致性验证在概念上可以用 GPT-4/Kimi 直接判断"生成内容是否被检索内容支持"。

**决策**：使用本地 **bge-reranker + uer/chinanli 双路融合** 做一致性验证，而非 LLM API 做 NLI。

**理由**：
1. **延迟不可控**：LLM API 调用通常 500ms-5s，无法满足 <60ms 的 Layer3 延迟目标。双路本地模型合计 <30ms。
2. **成本**：NLI 判断每次查询至少 1 次 API 调用，高频查询下成本不可接受。
3. **离线可用**：比赛现场网络不稳定时，本地模型确保核心功能不中断。
4. **准确率**：单模型（bge-reranker）对"矛盾"的召回有限。补充 uer/chinanli（专门 NLI 三分类模型）后，双路交叉验证显著提升 contradiction 检出率。
5. **模型极小**：uer/chinanli 仅 110MB，CPU 推理 <20ms，不增加架构负担。

**融合逻辑**：reranker 输出相似度分数（0~1）+ chinanli 输出三分类标签，任一模型触发 contradiction 即告警，双一致时高置信度阻断。

---

### ADR-003：为什么 ChromaDB 主用，而非直接上 pgvector？

**背景**：团队有 PostgreSQL 基础，考虑过直接用 pgvector。

**决策**：V1 用 ChromaDB，pgvector 作为预留扩展。

**理由**：
1. **开发速度**：ChromaDB 嵌入式模式无需管理数据库服务，开发期零运维负担。
2. **比赛现场**：ChromaDB 文件型持久化更容易备份和迁移。
3. **抽象层**：通过 `VectorStore` 抽象接口，后续切换成本极低。
4. **生态验证**：多个参考项目（trojan-rag-demo、Awesome-Rag-Attacks）使用 ChromaDB，有问题可对标。

---

### ADR-004：为什么采用双版本（GPU/CPU）部署策略？

**背景**：比赛现场设备环境不确定，可能只有 CPU，也可能有 GPU。

**决策**：准备 GPU 高性能版和 CPU 轻量化版两套配置，通过配置文件切换。

**理由**：
1. **现场环境不可控**：比赛举办方提供的设备可能是云服务器（有 GPU）或本地笔记本（无 GPU），无法提前确认。
2. **演示不容失败**：比赛演示是核心环节，系统必须能在任何环境下流畅运行。
3. **降级链清晰**：BGE-M3（完整）→ INT8 量化 → bge-small-zh（轻量）→ CPU 推理，每一步都有明确的性能/精度权衡。
4. **切换成本极低**：模型加载通过 `config/*.yaml` 控制，切换只需改配置文件，无需改代码。

**妥协**：CPU 版延迟目标放宽至 <500ms，但核心功能（检测率、阻断能力）不打折。

---

## 七、风险评估与缓解

| 风险 | 可能性 | 影响 | 缓解策略 |
|------|--------|------|---------|
| BGE-M3 本地推理显存不足 | 中 | 高 | 量化模型（INT8，显存降至 ~1GB）/ 降级 bge-small-zh（~500MB）/ CPU 推理 |
| Kimi API 免费额度用完 / 网络不可用 | 中 | 高 | 准备 DeepSeek API Key 作为备用 / 本地 Qwen2.5 INT4 fallback / 离线 Docker 镜像预装模型 |
| ChromaDB 并发性能不足 | 低 | 中 | V1 场景下并发低（演示级），不足时加内存缓存层 |
| HanLP 与 PyTorch 版本冲突 | 低 | 中 | 隔离测试 HanLP 安装，冲突时回退 jieba+正则 |
| 本地 NLI 模型准确率不达标 | 中 | 高 | 准备 cross-encoder/nli-deberta-v3-xsmall（110MB，专门 NLI）作为备选 |
| Gradio 界面功能受限 | 低 | 低 | 回退 Streamlit 或增加纯 API 端点演示 |
| **比赛现场无网络** | 中 | 极高 | **预构建 Docker 离线镜像**：含所有模型、依赖和数据，现场零下载 |
| **CPU 环境下延迟超标** | 中 | 高 | **双版本策略**：自动降级轻量模型，延迟放宽至 <500ms，核心检测功能保留 |
| **阈值未调优导致指标不达标** | 高 | 高 | **提前跑 threshold_sweep.py**：在 Week 3 完成参数扫描，锁定最优阈值 |
| **SOTA 对比数据缺失** | 中 | 高 | **Week 2-3 跑通 RAGDefender**：在相同数据集上跑出基线，生成对比图表 |

---

## 八、选型冻结确认

本报告中的技术选型在 **Week 1 对齐会** 后冻结。冻结后如需变更，需：
1. 变更发起者在团队群提出变更申请（含理由和影响分析）
2. 三人投票，2/3 同意方可变更
3. 变更后更新本文档版本号，同步修改 `requirements.txt`

| 选型项 | 状态 | 冻结日期 |
|--------|------|---------|
| Python 3.10 | 🟡 待冻结 | — |
| FastAPI | 🟡 待冻结 | — |
| BGE-M3 | 🟡 待冻结 | — |
| ChromaDB (主) | 🟡 待冻结 | — |
| Kimi API | 🟡 待冻结 | — |
| bge-reranker | 🟡 待冻结 | — |
| IF + LOF | 🟡 待冻结 | — |
| HanLP | 🟡 待冻结 | — |
| Gradio | 🟡 待冻结 | — |
| Docker Compose | 🟡 待冻结 | — |

---

*文档版本: v0.1 | 状态: 草案 | 下次评审: Week 1 对齐会 (冻结为目标)*
