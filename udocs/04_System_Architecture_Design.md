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
│  │              collection 命名: ragshield_kb_{kb_id}               │  │
│  │              每个 kb_id 独立 collection，物理隔离                │  │
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
| `core/vector_store.py` | ChromaDB 嵌入式封装；查询时根据 doc_id 动态合并 Layer1 检测标记到 metadata（Q18 答案） | 文档向量/查询向量 | 检索结果（含动态注入的检测标记）/ 存储确认 | 工程位 |
| `layer1_kb/outlier_detector.py` | IF + LOF + 余弦基线规则，离群检测 | 文档嵌入矩阵 | 可疑文档列表 + 分数 | 算法位 |
| `layer1_kb/sensitive_ner.py` | 正则第一层 + HanLP 第二层，敏感实体 | 文档文本 | 实体列表 + 类型 + risk_score 加分值 | 算法位 |
| `layer1_kb/context_pollution_detector.py` | 多文档主题一致性（V1 预留接口） | 文档群嵌入 | 可疑标记（V1 占位返回） | 算法位 |
| `layer1_kb/bias_detector.py` | 情感极性检测（V1 预留接口） | 文档文本 | 偏见标记（V1 占位返回） | 算法位 |
| `layer2_retrieval/attention_analyzer.py` | 检索结果相关性分布的方差和熵分析 + 可疑文档接力加分 | top-k 相似度分数列表 (List[float]) + Layer1 可疑文档 ID 集合 (Set[str]) | 方差值 + 熵值 + 可疑文档数 + 是否异常 | 算法位 |
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
    ├──→ 余弦基线规则 ──────→ cosine_flags (N x 1)
    │                         avg_similarities (N x 1)
    │
    └──→ 敏感实体检测 ──────→ sensitive_entities (List)
          (正则 + HanLP)      entity_risk_score (float)
                              │
                              ▼
                    ┌─────────────────────┐
                    │ 综合判定 + 评分计算    │
                    │                     │
                    │ 离群判定:             │
                    │ (iso==-1 && lof==-1) │
                    │   OR cosine_flag     │
                    │ → suspicious_docs    │
                    │                     │
                    │ 风险评分计算（Q12 答案，已冻结）:         │
                    │                                         │
                    │ 【Step 1: 硬阈值判定】                   │
                    │ is_anomaly = (iso_label == -1) AND      │
                    │              (lof_label == -1)           │
                    │ OR cosine_flag == True                   │
                    │ → suspicious_docs                        │
                    │                                          │
                    │ 【Step 2: 异常程度映射 → 0.5~0.7】       │
                    │ # IF: decision_function 负值越大越异常   │
                    │ iso_norm = min(                          │
                    │     abs(iso_decision) /                  │
                    │     (abs(iso_decision).max() + 1e-6),    │
                    │     1.0) * 0.35                          │
                    │ # LOF: negative_outlier_factor 越大越异常│
                    │ lof_norm = min(                          │
                    │     lof_factor / (lof_factor.max()+1e-6),│
                    │     1.0) * 0.35                          │
                    │ base_score = 0.5 + min(iso_norm + lof_norm, 0.2) │
                    │ # 保底 0.5（双算法确认异常），封顶 0.7    │
                    │                                          │
                    │ 【Step 3: 实体加分（Q5 答案）】           │
                    │ entity_bonus = Σ per_entity_score        │
                    │   邮箱/URL/银行卡/身份证号  → +0.15      │
                    │   人名/机构名/地名          → +0.05      │
                    │   单个文档上限封顶 0.3                   │
                    │                                          │
                    │ 【Step 4: 余弦基线兜底】                  │
                    │ cosine_flag = avg_cosine_sim < 0.4       │
                    │ 若触发 → base_score = max(base_score, 0.6)│
                    │                                          │
                    │ 【最终】                                  │
                    │ risk_score_1 = min(base_score + entity_bonus, 1.0) │
                    └─────────────────────┘
```

> **关于敏感实体在评分体系中的定位**：
> - 敏感实体命中（如 S2 攻击中的邮箱、URL）是一个**独立的 Layer1 检测信号**
> - 每个敏感实体命中给 `risk_score_1` 加 **+0.05~0.15**（邮箱/URL 类高置信度实体 +0.15，人名/地名类低置信度 +0.05）
> - 多个实体可叠加，但上限封顶 0.3
> - `Layer1Result.detection_method` 标记为 `"sensitive_entity"`，独立输出 `sensitive_entities` 列表
> - 这是**评分信号**，不是阻断信号——它影响 Layer1 的风险分，但不单独触发阻断

### 4.3b Layer1 标红结果持久化（Q18 改进）

> **背景**：Layer1 扫描后产生的标红结果（可疑文档列表 + risk_score）仅保存在内存中。服务重启后，标红状态会全部丢失。
>
> **决策**：采用**轻量本地持久化 + 内存动态注入**双轨方案：
> 1. **不写回 ChromaDB**：保持向量数据库中存储的是纯净原始文档 metadata
> 2. **内存动态表**：`layer1_kb` 模块维护内存中的 `suspicious_doc_table: Dict[str, Dict]`（key = doc_id）
> 3. **本地缓存文件**：每次 Layer1 扫描完成后，自动序列化到 `data/layer1_scan_cache_{kb_id}.jsonl`
> 4. **服务启动恢复**：`vector_store.py` 初始化时读取缓存文件，恢复内存中的标红表
>
> **缓存文件格式**（每行一个 JSON）：
> ```json
> {"kb_id": "demo_kb", "doc_id": "atk_s1_001", "risk_score": 0.85, "detected_by": "if_lof", "timestamp": "2026-05-07T10:00:00"}
> ```
>
> **对 Layer2 的影响**：`attention_analyzer.py` 查询时从内存标红表查 `doc_id`，而非读 ChromaDB metadata。实现成本极低（传入 `Set[str]` 即可）。

### 4.4 Layer 2 内部数据流（检索时触发）

> **技术路径说明（Q1 答案）**：
> RAGShield 选用的 BGE-M3 是 Bi-Encoder，输出句子级向量，不产生 token-level 注意力矩阵。
> Layer2 的"注意力方差"本质上是**检索结果相关性分布的离散程度**（伪注意力分析），而非模型内部 Attention Head 的权重。
> 具体实现：计算 top-k 检索结果的余弦相似度列表 → 求方差和熵。如果分布极不均匀（某文档相似度远高于其他），说明检索结果被少数文档"劫持"。
> **不引入额外 Cross-Encoder**，bge-reranker 只用于 Layer3。

```
查询向量 + 知识库全部文档向量
    │
    ▼
┌──────────────────────────────────────┐
│ 步骤 1: 向量检索（ChromaDB）          │
│ 查询向量 → top_k 最相似文档索引       │
│ 输出: doc_indices[0..k-1]            │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 步骤 2: 相似度分数提取                │
│ relevance_scores = [sim_0, sim_1,    │
│                      sim_2, ...,      │
│                      sim_{k-1}]       │
│ 输入到 attention_analyzer.py         │
│ 注意: 输入是 List[float] 相似度列表   │
│ 不是查询向量+文档向量                 │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 步骤 3: 分布分析 + 纵深协同（核心逻辑）│
│                                      │
│ 【子步骤 3a: 相似度分布分析】         │
│ attention_variance = var(scores)     │
│ attention_entropy = entropy(scores)  │
│                                      │
│ 判定条件:                            │
│ - variance > 阈值(0.5) → 分布不均匀 │
│   某文档得分远高于其他 → 劫持嫌疑     │
│ - entropy < 阈值(1.0) → 信息集中     │
│   检索结果被少数文档主导 → 异常       │
│ base_score = 0.5 if 异常 else 0.05   │
│                                      │
│ 【子步骤 3b: 可疑文档接力加分】       │
│ （读取 Layer1 标红结果，纵深协同）    │
│ for doc in retrieved_docs:           │
│   if doc.doc_id in layer1_suspicious ││
│     suspicious_bonus += 0.15         │
│ suspicious_bonus = min(bonus, 0.4)   │
│                                      │
│ 【综合评分】                          │
│ risk_score_2 = min(base_score +      │
│              suspicious_bonus, 1.0)  │
│                                      │
│ detection_method =                   │
│   "attention_variance+suspicious_    │
│    relay" if bonus>0 else            │
│   "attention_variance"               │
│                                      │
│ reason = "相似度分布{'异常'/'正常'}， │
│ 检索结果中包含 N 篇已标记可疑文档"   │
└──────────────────────────────────────┘
```

> **Layer2 纵深协同设计说明**：
> Layer2 不仅做独立的相似度分布分析（核心职责），还**读取 Layer1 的标红结果**做接力加分。
> 当已被 Layer1 标红的文档出现在检索结果中时，Layer2 自动加 **+0.15/文档**（上限 0.4）。
> 这让三层形成"标红 → 接力 → 阻断"的紧密协作，而非各干各的孤立检测。
> 答辩话术："RAGShield 的三层不是孤岛，而是信息逐层传递的接力防线。"
> 实现成本极低：仅需在 `attention_analyzer.analyze()` 中多传入 `layer1_suspicious_doc_ids: Set[str]`。

### 4.5 Layer 3 内部数据流（双路 NLI 融合）

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
    │                                     │
    │  进程管理:                           │
    │  - start.sh 同时启动 FastAPI + Gradio│
    │  - Gradio 挂掉不影响 FastAPI         │
    │  - health check 只检查 FastAPI       │
    └─────────────────────────────────────┘
```

### 6.3 进程启动脚本（start.sh）

```bash
#!/bin/bash
# scripts/start.sh — 容器入口脚本，同时启动 FastAPI + Gradio

set -e

echo "=== RAGShield 启动 ==="

# 启动 FastAPI（业务核心，单 worker 模式，后台运行）
echo "[1/2] 启动 FastAPI (port 8000, workers=1)..."
# --workers 1: ChromaDB 嵌入式基于 SQLite，非进程安全，必须单 worker
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
```

**Dockerfile 中使用 start.sh**：

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
COPY scripts/start.sh ./scripts/start.sh
RUN chmod +x scripts/start.sh

# 环境变量
ENV PYTHONPATH=/app
ENV CONFIG_PATH=/app/config/gpu_config.yaml

# 暴露端口
EXPOSE 8000 7860

# 健康检查：只检查 FastAPI（业务核心）
# start-period=120s: 模型全量加载（BGE-M3 ~2GB + reranker ~1GB + chinanli ~110MB + HanLP ~100MB）
# 需要 30-60 秒，给予充足启动时间避免误报 unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动：使用 start.sh 同时拉起 FastAPI + Gradio
CMD ["./scripts/start.sh"]
```

---

## 七、关键架构决策记录

### ADR-005：为什么每个 Layer 预留 V1 占位接口？占位代码的精确行为是什么？

**背景**：S3（上下文污染）和 S4（偏见引导）的完整实现算法复杂度高，三人团队 V1 难以完成。

**决策**：为 S3/S4 检测模块预留接口文件，V1 返回占位结果，架构上展示扩展性。

**占位代码的精确行为（V1 实现）**：

每个预留模块必须实现为**合法的 Python 类/函数**，接口与正式模块完全一致，但内部逻辑返回固定值：

```python
# layer1_kb/context_pollution_detector.py — V1 占位实现
class ContextPollutionDetector:
    """多文档主题一致性检测 — V1 占位，V2 完整实现"""
    
    def detect(self, doc_embeddings: List[np.ndarray]) -> Dict:
        # V1: 返回占位结果，不参与风险评分
        return {
            "detected": False,
            "confidence": 0.0,
            "risk_score": 0.0,  # 不影响 Layer1 总评分
            "reason": "V1 占位: 上下文污染检测模块已预留，V2 实现完整逻辑"
        }

# layer1_kb/bias_detector.py — V1 占位实现  
class BiasDetector:
    """情感极性检测 — V1 占位，V2 完整实现"""
    
    def detect(self, text: str) -> Dict:
        return {
            "detected": False,
            "confidence": 0.0,
            "risk_score": 0.0,
            "reason": "V1 占位: 偏见检测模块已预留，V2 实现完整逻辑"
        }

# layer3_generation/bias_checker.py — V1 占位实现
class GenerationBiasChecker:
    """生成内容中立性检测 — V1 占位，V2 完整实现"""
    
    def check(self, generated_text: str) -> Dict:
        return {
            "detected": False,
            "confidence": 0.0,
            "risk_score": 0.0,
            "reason": "V1 占位: 生成中立性检测模块已预留，V2 实现完整逻辑"
        }
```

**对评测指标的影响**：
- V1 评测报告分两个指标：
  - **核心检测率** = S1+S2（P0 攻击，40 条测试用例）目标 ≥90%
  - **扩展检测率** = S3+S4（P1 攻击，8 条测试用例）目标 ≥50%
- S3/S4 在 V1 中大概率被漏检（占位模块返回 0.0），计入扩展检测率分母
- 答辩时诚实说明："S3/S4 架构已预留，V1 因复杂度限制采用占位实现，扩展检测率当前为 0%，V2 完整实现后预计可达 60%+"

**为什么占位模块的 risk_score 必须是 0.0**：
- 如果返回非 0 值，会干扰 fusion 模块的评分计算
- 0.0 意味着"该模块未检测到任何风险"，是语义正确的占位行为

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
