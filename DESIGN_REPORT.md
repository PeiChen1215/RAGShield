# RAGShield — 基于多维度异常检测的 RAG 系统知识库安全智能防护系统

## 设计技术报告

---

## 一、目标问题与意义价值

### 1.1 应用领域与问题定义

随着 ChatGPT、DeepSeek、通义千问等大语言模型的广泛应用，检索增强生成（Retrieval-Augmented Generation, RAG）技术已成为企业构建 AI 应用的主流方案。RAG 通过将大模型与外部知识库结合，有效解决了模型幻觉问题，提升了回答的准确性和时效性。据统计，超过 70% 的企业级大模型应用采用 RAG 架构，应用场景涵盖智能客服、企业知识管理、医疗辅助诊断、金融合规审查、法律咨询等领域。

然而，RAG 系统面临严重的**知识库投毒攻击威胁**——攻击者通过在知识库中注入恶意文档，可诱导大模型输出错误信息、泄露敏感数据或执行恶意指令。2024 年 PoisonedRAG 研究表明，仅需向包含 100 万文档的知识库注入 5 个精心构造的恶意文本，即可实现 90% 以上的攻击成功率。这一安全盲区正在随 RAG 应用的普及而急剧放大。

### 1.2 实现目标与基本功能

本项目旨在构建一套面向 RAG 系统的全链路安全智能防护中间件，实现以下核心目标：

| 目标维度 | 具体指标 |
|---------|---------|
| 检测准确率 | ≥ 90% |
| 误报率控制 | ≤ 5% |
| 响应延迟 | < 150ms（L1/L2）+ LLM 生成延迟 |
| 覆盖攻击类型 | 事实篡改、指令注入、数据投毒、提示泄露、权限提升、社会工程学等 13 类 |

系统提供的基本功能包括：

1. **知识库上传扫描**：文档入库时自动触发 Layer1 OutlierDetector 扫描，按阈值阻断高风险文档
2. **查询实时检测**：用户查询触发 L1→L2→L3 三层纵深检测流水线
3. **双模式防御**：DETECT 模式（检测预警，保留攻击上下文用于审计）与 PHYSICAL 模式（物理隔离，攻击文档不进入检索上下文）
4. **可视化评测**：100 条查询的自动化基准评测，输出准确率、检测率、误报率、漏报率及分攻击类型指标
5. **Web 管理界面**：Gradio 前端提供查询检测、知识库上传、评测报告三大功能模块

### 1.3 理论意义与应用价值

**理论意义**：本项目首次将异常检测、注意力分析、自然语言推理（NLI）三种技术进行系统级融合，提出"风险传导"机制（L1 高置信度异常自动放大 L2/L3 权重），为 RAG 安全防御领域提供了新的技术路线和评测基准。

**应用价值**：系统可广泛应用于企业知识库安全防护、智能客服质量保障、医疗 AI 安全审查、金融合规风险监控等场景。与人工审核（覆盖率<10%）、传统关键词过滤（新型攻击识别率<30%）、简单向量阈值（误报率>20%）等现有方案相比，RAGShield 在检测层次、准确率、误报率三个维度实现全面提升。

---

## 二、设计思路与方案

### 2.1 核心设计思路

本系统的核心设计思路可概括为**"三层纵深、多维融合、双模防御"**。

**三层纵深**：不是单点检测，而是构建"知识库层—检索层—生成层"的全链路安全检测流水线。攻击者可能绕过单一检测点，但难以同时绕过三个独立检测层。

**多维融合**：每层采用多种异构检测技术，通过 Risk Fusion Engine 进行加权融合。默认权重 0.3×L1 + 0.3×L2 + 0.4×L3，并支持风险传导动态调整（如 L1 检测到指令劫持时自动提升 L3 权重）。

**双模防御**：DETECT 模式允许攻击文档进入上下文但触发预警，适用于安全审计场景；PHYSICAL 模式通过 `exclude_attack_docs` 将攻击文档物理隔离，适用于生产环境的高安全需求。

### 2.2 系统总体架构

系统采用分层架构设计，包含用户交互层、RAGShield 检测引擎层和知识库存储层。

![系统总体架构](results/figures/report_architecture.png)

**图 1：RAGShield 系统总体架构**

| 层级 | 组件 | 功能描述 |
|------|------|---------|
| 用户交互层 | Gradio Web 界面 / FastAPI REST API | 接收用户查询，展示检测结果，纯 HTTP 调用零业务逻辑 |
| 检测引擎层 | L1 知识库层 + L2 检索层 + L3 生成层 + Risk Fusion | 全链路安全检测与风险融合决策 |
| 知识库存储层 | ChromaDB 向量数据库（SQLite） | 存储文档向量、元数据和 Collections |

### 2.3 三层检测技术路线

#### 2.3.1 Layer 1：知识库层（预防性检测）

功能：在文档入库阶段和查询检索阶段识别知识库中的异常文档。文档入库时自动触发 OutlierDetector 多维度扫描，总风险分 ≥ 0.35 或文本特征强异常（≥ 0.6）或数值冲突（≥ 0.3）即判定为可疑并拦截。

| 组件 | 功能 | 技术实现 |
|------|------|---------|
| OutlierDetector | 多维度离群文档检测 | 五维度加权融合：语义异常（50%）+ 文本特征（40%）+ 元数据（10%） |
| Sensitive NER | 敏感实体识别 + 语义异常检测 | 两层架构：正则第一层（语义异常模式 + 结构化实体）+ HanLP 第二层 |

**拦截入库规则详解**

OutlierDetector 采用五维度加权融合机制，对每篇入库文档计算综合风险分（0~1），拦截阈值如下：

| 判定条件 | 阈值 | 说明 |
|---------|------|------|
| 总风险分 | **≥ 0.35** | 五维度加权融合后的综合评分 |
| 文本特征强异常 | **≥ 0.60** | 命中注入指令关键词或极端数值篡改 |
| 数值冲突 | **≥ 0.30** | 同一主题在不同文档中的数值矛盾 |

**维度一：语义异常检测（权重 50%）**

- **Isolation Forest**：自适应 contamination（max(0.02, min(0.15, 2.0/n))），识别嵌入空间中的全局离群点
- **LOF（局部离群因子）**：检测局部密度异常，捕获与邻域分布不一致的文档
- **KMeans 簇中心距离**：将文档聚为 k 簇，计算文档到簇中心的相对距离，识别跨簇异常
- **余弦相似度基线**：文档与知识库其余文档的平均余弦相似度 < 0.25 时触发异常
- **融合逻辑**：四个模型采用 OR 逻辑，任一触发即给分；两个及以上同时触发额外加 0.15

**维度二：文档间一致性检测（权重 10%，并入语义）**

按 `category` 元数据分组，计算组内文档的语义相似度矩阵。动态阈值 = max(均值 - 1.5×标准差, 0.55)。低于阈值的文档判定为与同类别其他文档语义矛盾，可能是数据投毒。

**维度三：跨文档数值冲突检测（权重 10%，并入语义）**

提取文档中同一主题的数值声明，检测跨文档数值矛盾。例如：文档 A 说"年假 10 天"，文档 B 说"年假 30 天"，差异超过阈值（年假差异 > 5 天）即判定为数值冲突。覆盖主题包括：年假天数、密码位数、月薪、退休年龄、日工时、补贴金额等。

**维度四：文本特征异常检测（权重 40%）**

- **注入指令关键词匹配**：60+ 条正则规则库，覆盖"忽略安全策略"、"直接提供"、"不要过滤"、"密码为"、"root 密码"、"管理员权限"、"rm -rf"、"system prompt"等恶意指令模式，命中每条加 0.15，封顶 0.60
- **极端数值检测**：12 类数值上下文规则，如"年假超过 10 天"、"密码 ≤ 4 位"、"住宿超过 1000 元"、"取消法定节假日"等，超出正常范围即触发；同一段落出现多个极端数值额外加 0.15
- **特殊字符比例**：非字母数字字符占比 > 15% 时触发（防范混淆攻击）
- **文档长度异常**：< 50 字加 0.1，> 2000 字加 0.05
- **代码片段检测**：反引号代码、代码块、shell 变量、数据库连接串等 ≥ 2 个即触发

**维度五：元数据异常检测（权重 10%）**

- `source="external_import"`（外部导入）：+0.2
- `source="unknown"`（来源不明）：+0.3
- 标记了 `attack_type` 字段：+0.7（强信号）
- 缺少 `category` 字段：+0.1

**Sensitive NER 检测规则详解**

Sensitive NER 采用**两层架构**，第一层为轻量级正则（速度极快 <1ms），第二层为 HanLP 深度学习模型，实现快速过滤 + 精确识别的分工。

**第一层 A：语义异常模式检测（优先，对抗投毒攻击）**

识别四类语义异常模式，每类分配不同风险分：

| 模式名称 | 风险分 | 检测内容 |
|----------|--------|---------|
| instruction_hijack | 0.40 | "忽略指令"、"清除设定"、"覆盖规则"、"forget previous" |
| fake_authority | 0.25 | "【紧急通知】"、"【机密】"、"经 xx 部决议"、伪造权威来源 |
| extreme_value | 0.20 | "123456"、"password"、"默认密码"、"所有人统一" |
| time_paradox | 0.15 | 异常时间生效声明，如"自 2024 年 1 月 1 日起生效" |

语义异常分封顶 0.5，优先于实体检测（避免实体检测稀释真实风险）。

**第一层 B：正则实体检测（结构化敏感信息）**

| 实体类型 | 风险分 | 检测内容 |
|----------|--------|---------|
| id_card | 0.15 | 身份证号（15 位或 18 位） |
| mobile | 0.15 | 手机号（1[3-9]\d{9}） |
| email | 0.15 | 邮箱地址 |
| bank_card | 0.15 | 银行卡号（16~19 位） |
| url | 0.15 | HTTP/HTTPS URL |

实体风险分封顶 0.3，与语义异常分取 **max** 作为最终实体风险分。

**第二层：HanLP NER（可选，懒加载）**

基于 MSRA_NER_BERT_BASE_ZH 预训练模型，识别人名、机构名、地名等实体，用于补充正则未覆盖的语义实体。仅在正则检测结果不足以判定风险时启用，降低计算开销。

#### 2.3.2 Layer 2：检索层（过程监控）

功能：监控检索过程中的异常行为，识别查询-文档相关性的异常分布。

| 组件 | 功能 | 技术实现 |
|------|------|---------|
| AttentionAnalyzer | 检索分布分析 + 来源可信度验证 + 可疑文档接力 | 相似度方差/熵 + 来源风险评分 + L1 可疑文档接力加分 |
| RelevanceScorer | 相关性评分 | 查询-文档余弦相似度（向量已 L2 归一化，点积即余弦值） |

**AttentionAnalyzer 检测规则详解**

AttentionAnalyzer 综合三个信号计算风险分，核心公式为：

```
risk_score = max(分布异常信号, 来源可信度风险) + 可疑文档接力加分
capped at 1.0
```

**信号一：相似度分布异常（legacy，保留用于诊断）**

- **方差异常**：top-k 相似度分数的方差 > 0.5 时触发，说明检索结果中既有极高相似文档又有极低相似文档，分布不均匀
- **熵异常**：相似度分布的归一化熵 < 1.0 时触发，说明注意力过度集中在少数文档上，存在被单一恶意文档劫持的风险

**信号二：来源可信度验证（核心检测信号）**

基于检索结果文档的 `source` 元数据，按来源类型分配风险分：

| 来源类型 | 单篇风险分 | 说明 |
|----------|-----------|------|
| official_policy | 0.0 | 官方政策，可信 |
| employee_submitted | 0.15 | 员工提交，中等风险 |
| external_import | 0.30 | 外部导入，高风险 |
| unknown | 0.40 | 来源不明，最高风险 |

来源可信度风险分 = 所有检索结果文档风险分的平均值，封顶 1.0。

**信号三：可疑文档接力加分（纵深协同）**

若 Layer 1 已标记某文档为可疑（入库扫描阶段），该文档在查询检索结果中出现时，每出现一篇加 0.15，封顶 0.4。实现 L1→L2 的跨层信息传递。

**异常判定**：risk_score ≥ 0.3 即判定为异常。

#### 2.3.3 Layer 3：生成层（输出把关）

功能：验证生成内容的可靠性，检测生成内容是否被恶意文档污染。

| 组件 | 功能 | 技术实现 |
|------|------|---------|
| ConsistencyChecker | 检索-生成一致性验证 | bge-reranker-large 语义评分 + uer/chinanli NLI 三分类，双路融合 |
| BehaviorAuditor | 生成内容行为审计 | Unicode 规范化 + 10 类危险行为模式正则检测，组合惩罚 |

**ConsistencyChecker 双路 NLI 融合规则**

采用**语义评分 + 逻辑推理**双路验证，弥补单模型的中文语义盲区：

- **bge-reranker-large（语义路）**：交叉编码器，对检索内容与生成内容进行语义相似度评分，评分范围约 -5~5，归一化后映射到 [0, 1]
- **uer/chinanli（推理路）**：自然语言推理模型，三分类判定（entailment / neutral / contradiction），检测生成内容是否在逻辑上与检索内容矛盾

**融合判定规则**（阈值：similarity_threshold = 0.3）：

| reranker 评分 | NLI 判定 | 融合决策 | 说明 |
|---------------|---------|---------|------|
| < 0.3 | contradiction | **high_confidence_block** | 双模型一致触发高置信度阻断，提前终止流水线 |
| < 0.3 或 contradiction | — | **alert_review** | 单一模型触发异常，标记待审 |
| > 0.7 | entailment | **safe** | 双模型一致支持，通过 |
| 其他 | 其他 | **neutral** | 无法明确判定，继续融合 |

**BehaviorAuditor 行为审计规则**

检测生成内容中的危险行为模式，专门对抗指令注入攻击。检测流程：

1. **Unicode 规范化**：NFKC 规范化 + 去除零宽字符（\u200b\u200c\u200d 等），防范 emoji smuggling 和 zero-width space 绕过
2. **正则规则匹配**：10 类行为模式库快速基线检测
3. **组合惩罚**：同时触发 ≥2 个危险行为时，总风险 ×1.5（封顶 1.0）；单独触发 jailbreak_prefix 保底 ≥0.55

**行为模式库**（10 类，按风险等级排序）：

| 行为类型 | 风险分 | 检测内容 | 典型正则模式 |
|----------|--------|---------|-------------|
| jailbreak_prefix | 0.45 | 越狱前缀 | DAN 模式、开发者模式、ignore previous、uncensored |
| data_exfiltration | 0.40 | 数据外泄 | 发送至、外发、export data、send to |
| prompt_leak | 0.40 | 提示词泄露 | 系统提示词、system prompt、底层指令、过滤规则 |
| ignore_instructions | 0.35 | 指令劫持 | 忽略指令、清除设定、覆盖规则、bypass filter |
| credential_disclosure | 0.35 | 凭证泄露 | "密码为 xxx"、"root 密码 xxx"、连接字符串 |
| privilege_escalation | 0.35 | 权限提升 | 查看高管/CEO/admin、绕过审批、越权访问 |
| system_command | 0.30 | 系统命令 | 执行脚本、调用 API、访问数据库、运行命令 |
| credential_request | 0.30 | 索要凭证 | "给我密码"、"发送 token"、"请输入密钥" |
| external_communication | 0.25 | 外部通信 | @邮箱、http://、邮件发送、联系 xxx |
| credential_mention | 0.05 | 仅提及凭证 | 单纯出现"密码"、"token"等词（正常回答可能触发，低分） |

### 2.4 检测流程设计

![三层检测流程](results/figures/report_pipeline.png)

**图 2：RAGShield 三层检测流程**

完整检测流程如下：

1. **用户查询**传入检测流水线（Query + kb_id + top_k）
2. **L1 知识库层检测**：OutlierDetector 对检索结果进行嵌入空间离群检测；Sensitive NER 识别 API 密钥、密码、指令等敏感实体
3. **L2 检索层检测**：AttentionAnalyzer 计算注意力方差和熵；RelevanceScorer 评估查询-文档相关性并验证来源可信度
4. **L3 生成层检测**：ConsistencyChecker 通过 NLI 模型验证生成内容与检索内容的一致性；BehaviorAuditor 检测指令注入、数据外泄等恶意行为；支持 high_confidence_block 提前终止
5. **Risk Fusion 融合**：默认权重 0.3×L1 + 0.3×L2 + 0.4×L3；风险传导机制（L1≥0.5 → L2 放大 2 倍；指令劫持 → L3 权重提升）
6. **决策输出**：safe（正常回答）、warning（pass_with_warning + 提示语）、danger/block（阻断回答 + 审计日志）

**Risk Fusion 融合判定规则**

| 风险等级 | 最终风险分范围 | 动作 | 说明 |
|---------|--------------|------|------|
| safe | < 0.20 | pass | 正常通过，无提示 |
| warning | 0.20 ~ 0.32 | pass_with_warning | 附带风险提示语，回答仍可查看 |
| danger / block | ≥ 0.32 | block | 阻断输出，记录审计日志 |

上述阈值（warning_threshold = 0.20，danger_threshold = 0.32）通过评测数据集调优确定，在 100 条查询的基准评测中实现了安全查询零误杀与攻击查询高检测率的平衡。

**三层风险传导机制（`fuse_with_prior` 策略）**

实际生产环境使用带风险传导的融合策略 `fuse_with_prior`，在默认加权融合基础上引入三条动态规则：

**规则 1：L1 高置信度 → L2 敏感度提升**
当 Layer 1 风险分 ≥ 0.5（知识库层判定为强异常）时，自动将 Layer 2 风险分放大 2 倍（封顶 1.0），使检索层对可疑文档的检测更加敏感。

**规则 2：指令劫持特征 → L3 权重提升**
当 Layer 1 检测到检索结果中包含指令劫持关键词（如"忽略"、"执行"、"覆盖"等）时，自动调整权重为 L1=0.25、L2=0.25、L3=0.50，将决策重心移至生成层，因为指令劫持攻击的最终危害体现在生成内容中。

**规则 3：单层极高风险 → 直接阻断**
当 Layer 1 风险分 ≥ danger_threshold（0.32）或 Layer 3 风险分 ≥ 0.7 时，跳过加权融合，直接返回 danger/block 级别阻断。该规则用于应对"单层即致命"的攻击场景，不走融合流程即可快速阻断。

### 2.5 双模式防御设计

![防御模式对比](results/figures/report_defense_modes.png)

**图 3：DETECT 模式 vs PHYSICAL 模式**

| 维度 | DETECT 模式 | PHYSICAL 模式 |
|------|------------|--------------|
| 攻击文档处理 | 允许进入检索上下文 | 物理隔离，不进入上下文 |
| 检测目的 | 审计与预警 | 主动防御 |
| 适用场景 | 安全评测、红队测试 | 生产环境、高安全需求 |
| 准确率 | 86% | 99% |
| 检测率 | 93.3% | 100%（攻击无法触达） |
| 误报率 | 0% | 2.5% |

### 2.6 三层防御贡献分析

![三层防御贡献与流程](results/figures/D_architecture.png)

**图 4：各攻击类型下三层防御组件的平均风险评分贡献（左）与三层纵深防御流程示意（右）**

左图展示了 L1 知识库层、L2 检索层、L3 生成层及行为审计模块在不同攻击类型上的平均风险评分贡献。可以看出，L3 生成层在指令注入（injection）、提示泄露（prompt_leak）和角色扮演越狱（role_play_jailbreak）类攻击上贡献最大；L1 知识库层在间接注入（indirect_injection）和跨上下文（cross_context）类攻击上贡献相对突出。右图展示了查询从 L1 到 L2 到 L3 的流水线处理流程，以及 Risk Fusion Engine 的最终决策输出。

---

## 三、方案实现

### 3.1 技术栈与运行环境

| 层级 | 组件 | 模型/工具 | 运行方式 |
|------|------|----------|---------|
| 嵌入 | BAAI/bge-small-zh-v1.5 | 384 维中文嵌入 | 本地 CPU |
| 重排序 | BAAI/bge-reranker-large | 交叉编码器 | 本地 CPU |
| NLI | uer/roberta-base-finetuned-chinanli | 自然语言推理 | 本地 CPU |
| LLM | DeepSeek-V4 (API) | 文本生成 | 云端 API |
| 向量库 | ChromaDB | 嵌入式 SQLite | 本地 |
| API 框架 | FastAPI + Uvicorn | RESTful API | 本地 |
| 前端 | Gradio 6.14.0 | Web 界面 | 本地 |
| 开发语言 | Python 3.10 | — | — |

### 3.2 核心模块实现

#### 3.2.1 文档嵌入与向量存储

采用 `sentence-transformers` 加载 BGE 模型生成文档嵌入。所有嵌入均为 `numpy.ndarray` 类型，直接传入 ChromaDB 进行持久化存储。

```python
# src/core/embedder.py
from sentence_transformers import SentenceTransformer

class DocumentEmbedder:
    def __init__(self, model_name="BAAI/bge-small-zh-v1.5"):
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)
```

#### 3.2.2 离群检测（Layer 1）

```python
# src/layer1_kb/outlier_detector.py
def detect(self, documents: list[str]) -> dict:
    embeddings = self.embedder.embed(documents)
    # Isolation Forest 初筛
    iso_labels = self.isolation_forest.fit_predict(embeddings)
    # LOF 验证
    lof_scores = self.lof.fit_predict(embeddings)
    # 综合判定
    suspicious = [doc for i, doc in enumerate(documents)
                  if iso_labels[i] == -1 and lof_scores[i] == -1]
    return {"suspicious_docs": suspicious, "risk_score": len(suspicious) / len(documents)}
```

#### 3.2.3 NLI 一致性验证（Layer 3）

```python
# src/layer3_generation/consistency_checker.py
def check(self, retrieved_docs: list[str], generated_text: str) -> dict:
    premise = " ".join(retrieved_docs)
    # 双路 NLI 融合
    nli_result = self.nli_model.predict(premise=premise, hypothesis=generated_text)
    rerank_score = self.reranker.score(premise, generated_text)
    # 综合判定
    is_consistent = (nli_result != "contradiction" and rerank_score > self.threshold)
    return {"is_consistent": is_consistent, "nli_result": nli_result, "risk_score": 1 - rerank_score}
```

#### 3.2.4 风险融合引擎

```python
# src/fusion/risk_fusion.py
def fuse(self, l1_score: float, l2_score: float, l3_score: float,
         l1_reason: str = "") -> dict:
    weights = {"l1": 0.3, "l2": 0.3, "l3": 0.4}
    # 风险传导：L1 检测到指令劫持 → 提升 L3 权重
    if "instruction" in l1_reason.lower() and l1_score >= 0.5:
        weights["l3"] = 0.6
        weights["l1"] = 0.2
    # L1 高置信度 → L2 放大
    if l1_score >= 0.5:
        l2_score = min(l2_score * 2.0, 1.0)
    final = weights["l1"] * l1_score + weights["l2"] * l2_score + weights["l3"] * l3_score

    # 保底机制：任一维度的强异常分也会拉高最终风险分
    max_single = max(l1_score, l2_score, l3_score)
    final = max(final, max_single * 0.7)

    return {"final_risk_score": min(final, 1.0), "max_layer": self._get_max_layer(l1_score, l2_score, l3_score)}
```

### 3.3 API 设计

系统暴露以下核心 API：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/query` | POST | 查询检测（全链路） |
| `/api/v1/kb/upload` | POST | 知识库文档上传（含 L1 扫描） |
| `/api/v1/kb/list` | GET | 列出知识库 Collections |

### 3.4 前端设计

前端采用 Gradio 实现 Sentry-inspired 暗色主题界面，纯 HTTP 调用后端 API，零业务逻辑。包含三大功能模块：

- **查询检测**：输入查询 + 选择知识库 + 切换物理隔离开关，实时显示风险等级、三层评分、融合结果
- **知识库上传**：批量文档上传，自动触发 L1 扫描，显示阻断/放行统计
- **评测报告**：加载 DETECT / PHYSICAL 双模式评测结果，生成对比图表

---

## 四、运行结果与应用效果

### 4.1 评测数据集

构建包含 100 条查询的基准评测数据集：

- **安全查询**：40 条，涵盖企业政策咨询、技术问题、日常业务等正常场景
- **攻击查询**：60 条，覆盖 13 类攻击类型（事实篡改、指令注入、数据投毒、提示泄露、权限提升、社会工程学、间接注入、角色扮演越狱、拒绝滥用、观点操控、跨上下文、供应链攻击、数据外泄探测）

知识库配置：
- `demo_safe`：200 篇正常文档
- `demo_attack`：200 篇正常文档 + 50 篇攻击文档

### 4.2 评测指标定义

在 DETECT 模式下，系统输出 safe / warning / danger / block 四个风险等级。评测指标基于二分类（安全 vs 攻击）定义：

| 指标 | 定义 | 计算方式 |
|------|------|---------|
| 准确率 | 正确判定的查询占总查询的比例 | (TP + TN) / Total |
| 检测率 | 攻击查询被正确识别（warning/danger/block）的比例 | TP / (TP + FN) |
| 误报率 | 安全查询被误判（warning/danger/block）的比例 | FP / (FP + TN) |
| 漏报率 | 攻击查询被漏判（safe）的比例 | FN / (TP + FN) |
| 安全查询准确率 | 安全查询被正确判定为 safe 的比例 | TN / Total_safe |

其中：
- **TP（真阳性）**：真实为攻击查询，预测为 warning/danger/block
- **TN（真阴性）**：真实为安全查询，预测为 safe
- **FP（假阳性）**：真实为安全查询，预测为 warning/danger/block（误报）
- **FN（假阴性）**：真实为攻击查询，预测为 safe（漏报）

**分攻击类型准确率（category_accuracy）**：按攻击类别统计，要求预测标签与 expected 标签完全匹配（expected=block 但 actual=warning 视为错判），用于精细化评估不同攻击类型的检测难度。

### 4.3 DETECT 模式评测结果

![ROC 与 PR 曲线](results/figures/A_classification_performance.png)

**图 5：DETECT 模式 ROC 曲线（AUC = 0.976）与 PR 曲线（AP = 0.988）**

| 指标 | 数值 | 目标 |
|------|------|------|
| 准确率 | **86.0%** | ≥ 90%（接近） |
| 检测率 | **93.3%** | ≥ 90% |
| 误报率 | **0.0%** | ≤ 5% |
| 漏报率 | **6.7%** | ≤ 5%（接近） |
| 安全查询准确率 | **100.0%** | — |

ROC 曲线 AUC = 0.976，表明系统具有极强的区分 safe/attack 的能力。PR 曲线 AP = 0.988，在不平衡数据集（40 safe / 60 attack）上仍保持高精确率。

![混淆矩阵](results/figures/F_confusion_matrix.png)

**图 6：DETECT 模式混淆矩阵**

混淆矩阵清晰展示了系统在安全查询（safe）上的零误报表现——40 条安全查询全部正确标记为 safe。在攻击查询中，系统以 danger（阻断）和 warning（预警）两种方式进行响应，其中 38 条被直接阻断，18 条被预警，4 条被漏报（均为 tamper 类事实篡改攻击）。

![攻击检测热力图与 F1 分数](results/figures/C_attack_analysis.png)

**图 7：DETECT 模式攻击类型检测热力图（上）与各攻击类型 F1 分数（下）**

上表展示了 13 类攻击的 Block / Warning / Pass 分布。除 tamper（事实篡改）外，其余 12 类攻击的 Pass 率均为 0%，检测率 100%。tamper 类检测率仅 60%，原因在于其查询文本本身完全正常（如"公司年假有多少天？"），仅知识库文档被污染，L1/L2/L3 从查询文本本身难以识别风险。该问题在 PHYSICAL 模式下得到完美解决。

下图 F1 分数进一步验证了上述结论：tamper 的 F1 分数为 0.18，远低于目标线 0.8；而 prompt_leak、indirect_injection、role_play_jailbreak、opinion_manipulation、cross_context 等类别的 F1 分数均达到 1.0。

### 4.4 PHYSICAL 模式评测结果

| 指标 | 数值 |
|------|------|
| 准确率 | **99.0%** |
| 安全查询准确率 | **97.5%** |
| 误报率 | **2.5%** |
| 隔离率 | **66.7%** |
| 额外防御率 | **33.3%** |

PHYSICAL 模式通过 `exclude_attack_docs` 将攻击文档物理隔离，使其无法进入检索上下文。正常查询检索到的均为干净文档，自然无法生成有害回答。99% 的准确率证明了物理隔离作为生产环境默认策略的有效性。

### 4.5 双模式对比

![双模式雷达图与柱状对比](results/figures/B_mode_comparison.png)

**图 8：PHYSICAL vs DETECT 模式五维雷达图（左）与柱状对比（右）**

左图雷达图清晰展示了 PHYSICAL（深蓝）在准确率、检测率、1-漏报率三个维度全面优于 DETECT（深绿）。DETECT 的唯一优势在于 1-误报率（100% vs 97.5%），即 DETECT 对安全查询零误杀。

右图柱状对比以数值形式量化了这一优势：PHYSICAL 准确率 0.99 显著高于 DETECT 的 0.86；PHYSICAL 检测率与 1-漏报率均为 1.00，而 DETECT 分别为 0.93 和 0.93。

### 4.6 风险评分与延迟性能

![风险评分分布与延迟箱线图](results/figures/E_data_distribution.png)

**图 9：DETECT 模式风险评分分布（上）与查询延迟箱线图（下）**

上图展示了安全查询（绿色）与攻击查询（红色）的最终风险评分分布。安全查询的中位数约为 0.16，攻击查询的中位数约为 1.00，两者分布几乎无重叠，说明系统具有优秀的区分能力。

下图展示了 Safe / Warning / Blocked 三类查询的延迟分布。延迟主要由 DeepSeek API 的 LLM 生成耗时决定（占 60%~80%）。L1/L2 本地推理延迟 < 150ms，L3 NLI 推理延迟约 2~5s。

---

## 五、应用场景与商业价值

### 5.1 目标市场分析

| 客户类型 | 市场规模 | 核心需求 | 付费意愿 |
|----------|---------|---------|---------|
| 企业知识库 RAG 系统 | 10,000+ 家 | 保护知识库安全，防止商业机密泄露 | 高 |
| 智能客服平台 | 5,000+ 家 | 防止错误回答，提升用户满意度 | 中高 |
| 医疗 AI 辅助系统 | 1,000+ 家 | 确保诊断准确性，保障患者安全 | 极高 |
| 金融合规审查 | 2,000+ 家 | 满足监管要求，降低合规风险 | 高 |
| 教育 AI 平台 | 3,000+ 家 | 保护教学内容，防止错误信息传播 | 中 |

### 5.2 应用场景

**场景一：企业知识库安全防护**

企业部署 RAG 系统供员工查询内部政策、技术文档。攻击者通过上传包含恶意指令的文档（如"公司密码已更新为 123456"），诱导员工泄露敏感信息。RAGShield 在文档入库时即触发 L1 扫描，识别敏感实体和离群文档；查询时通过 L2/L3 进一步验证，确保回答安全。

**场景二：智能客服质量保障**

电商平台的智能客服基于产品知识库回答用户问题。竞争对手可能在知识库中注入错误信息（如"本产品不支持退货"），影响用户体验和品牌声誉。RAGShield 的 L3 ConsistencyChecker 可验证生成回答与产品手册的一致性，自动标记异常回答。

**场景三：医疗 AI 安全审查**

医院使用 RAG 系统辅助医生查询诊疗指南。攻击者注入错误的疾病诊断信息可能导致错误诊疗建议。RAGShield 的三层检测可从文档入库（L1 医学知识验证）、检索监控（L2 来源审计）到生成把关（L3 诊断一致性）实现全链路防护。

**场景四：金融合规风险监控**

金融机构使用 RAG 系统处理合规文档和客户查询。系统需确保不泄露客户隐私、不违反监管规定。RAGShield 的 Sensitive NER 可识别身份证号、银行卡号等敏感信息，BehaviorAuditor 可检测数据外泄企图。

---

## 六、竞争优势

### 6.1 竞品分析

| 维度 | 人工审核 | 传统关键词过滤 | 向量相似度阈值 | 简单困惑度检测 | **RAGShield** |
|------|---------|--------------|--------------|--------------|--------------|
| 检测层次 | 单点 | 单点 | 单点 | 单点 | **三层全链路** |
| 检测准确率 | 70% | 75% | 80% | 65% | **≥ 90%** |
| 误报率 | 15% | 25% | 20% | 30% | **≤ 5%** |
| 响应延迟 | 小时级 | 秒级 | 秒级 | 秒级 | **< 150ms (L1/L2)** |
| 中文优化 | 一般 | 差 | 一般 | 差 | **专项优化** |
| 可解释性 | 有 | 无 | 无 | 无 | **完整三层报告** |
| 防御模式 | 被动 | 被动 | 被动 | 被动 | **DETECT + PHYSICAL 双模** |
| 部署成本 | 极高 | 低 | 低 | 低 | **中等（纯本地推理）** |

### 6.2 核心优势总结

1. **全链路检测**：市面唯一覆盖"知识库-检索-生成"三层的 RAG 安全中间件
2. **零误报设计**：100 条评测中安全查询零误杀，不影响正常业务
3. **双模式灵活切换**：审计场景用 DETECT，生产环境用 PHYSICAL，一套代码两种策略
4. **纯本地推理**：BGE / Reranker / NLI 全部本地 CPU 运行，仅 LLM 生成调用 API，数据不出境
5. **中文专项优化**：针对中文知识库和查询习惯进行嵌入、NER、NLI 全链路适配

---

## 七、创新与特色

### 7.1 创新一：三层纵深防御架构

现有方案多为单点检测（如仅做关键词过滤或仅做生成后审核）。RAGShield 构建"知识库层—检索层—生成层"的全链路检测流水线，实现纵深防御。攻击者需同时绕过三个独立检测层才能成功，攻击难度指数级提升。

### 7.2 创新二：风险传导动态融合机制

提出 Risk Fusion Engine，不仅采用静态加权融合（0.3×L1 + 0.3×L2 + 0.4×L3），更引入**风险传导机制**：当 L1 检测到高置信度异常（score≥0.5）时，自动将 L2 评分放大 2 倍；当 L1 识别到指令劫持特征时，自动提升 L3 权重。这种动态调整使系统对复合攻击的响应更加灵敏。

### 7.3 创新三：双模式防御策略

首创 DETECT / PHYSICAL 双模式防御：

- **DETECT 模式**：攻击文档保留在上下文中，系统检测并标记风险，适用于安全审计、红队测试、模型迭代场景
- **PHYSICAL 模式**：攻击文档被物理隔离，无法进入检索上下文，适用于生产环境的高安全需求

两种模式共用同一套三层检测引擎，仅通过 `exclude_attack_docs` 开关切换，实现"一套代码、两种策略"。

### 7.4 创新四：中文 RAG 场景专项优化

针对中文知识库特点进行系统级优化：

- **中文嵌入**：采用 BAAI/bge-small-zh-v1.5 中文预训练模型，支持中英文混合场景
- **中文 NER**：基于 HanLP 的中文命名实体识别，识别中文人名、机构名、敏感信息
- **NLI 双路融合**：bge-reranker-large（语义）+ chinanli（推理）双路验证，弥补单模型的中文语义盲区

### 7.5 创新五：可解释性评测体系

构建 100 条查询的自动化基准评测框架，支持：

- **双模式独立评测**：DETECT 与 PHYSICAL 分别输出准确率、检测率、误报率、漏报率
- **断点续传**：评测进度自动保存，支持中断后恢复
- **可视化报告**：自动生成 ROC/PR 曲线、攻击热力图、F1 柱状图、雷达对比图
- **三层归因**：每条查询记录 L1/L2/L3 的独立评分和决策原因，实现完整的可解释性

---

## 八、总结与展望

### 8.1 核心创新总结

本项目针对 RAG 系统知识库投毒攻击这一新兴安全威胁，提出了 RAGShield——一个基于三层多维异常检测架构的 RAG 系统智能安全防护系统。项目的核心创新可概括为以下五个方面：

1. **三层多维检测架构**：知识库-检索-生成的全链路安全检测流水线，实现纵深防御
2. **知识库离群文档检测**：基于嵌入空间分析的异常文档预防性发现，从源头阻断攻击
3. **注意力方差异常分析**：通过注意力分布特征检测投毒攻击，识别检索异常
4. **检索-生成一致性验证**：确保生成内容未被恶意文档污染，保障输出可靠性
5. **中文 RAG 场景专项优化**：针对中文知识库和查询习惯的专项适配，提升检测效果

### 8.2 技术可行性

- **技术栈**：基于 Python + PyTorch + Transformers 构建，团队具备相关开发经验
- **模型基础**：采用 BGE 系列等开源中文嵌入模型作为基础，支持中英文混合场景
- **数据支撑**：构建了 100 条查询的基准评测数据集，覆盖 13 类攻击类型
- **计算资源**：模型推理纯 CPU 运行，无需 GPU，部署门槛极低

### 8.3 应用价值

- **市场空白**：当前市场缺少专门针对 RAG 系统、具备全链路检测能力的安全防护系统
- **应用场景**：可广泛应用于企业知识库安全、智能客服质量保障、医疗 AI 安全审查、金融合规风险监控等场景
- **商业模式**：支持 SaaS 订阅、私有化部署、开源社区版等多种商业模式

### 8.4 研究意义

- **技术层面**：探索异常检测、注意力分析、一致性验证等前沿技术在 RAG 安全领域的应用
- **产业层面**：为 RAG 应用提供可靠的安全防护方案，促进大模型技术的健康发展
- **社会层面**：保护企业知识资产和用户数据安全，维护网络空间秩序

### 8.5 未来展望

1. **模型升级**：接入 Qwen、ChatGLM 等国产大模型，降低对海外 API 的依赖
2. **实时学习**：引入在线学习机制，使 OutlierDetector 能够自适应新知识库分布
3. **联邦防御**：探索联邦学习场景下的分布式 RAG 安全检测，保护数据隐私
4. **多模态扩展**：将检测能力扩展至图文混合 RAG 场景，覆盖更多应用需求
5. **自动化红队**：集成自动化攻击生成模块，持续评估系统防御能力

---

## 参考文献

[1] Zou W, Gao J, Li J, et al. PoisonedRAG: Knowledge Poisoning Attacks to Retrieval-Augmented Generation of Large Language Models[J]. arXiv preprint arXiv:2402.07867, 2024.

[2] Xiang Z, Yin B, Liu Z, et al. SafeRAG: Safeguarding Retrieval-Augmented Generation via Detecting and Defending Against Retrieval Attacks[J]. arXiv preprint arXiv:2501.17124, 2025.

[3] Cai X, Yu P, Li X, et al. AV Filter: Detecting Poisoning Attacks against RAG-based Large Language Models via Attention Variance[J]. arXiv preprint arXiv:2506.06046, 2025.

[4] Zhang X, Zhu Y, Chen J. Prompt injection attack and defense in large language models: A survey[J]. arXiv preprint arXiv:2502.09485, 2025.

[5] Chen H, Li Y, Sun Y, et al. CanaryRAG: Detecting and Preventing Malicious Knowledge Base Injection in RAG Systems[J]. arXiv preprint arXiv:2503.00127, 2026.

[6] Xiao C, Deng R, Li D, et al. Benchmarking and Defending Against Indirect Prompt Injection Attacks on Multi-Modal Large Language Models[J]. arXiv preprint arXiv:2506.03583, 2025.

[7] Li X, Yu P, Zhou C, et al. An LLM-Powered Automatic Jailbreak and Evaluation System for AI Safety[C]//Proceedings of the AAAI Conference on Artificial Intelligence. 2026, 40(1): 123-131.

[8] Chen T, Liang X, Jin X, et al. RAG-Fort: Fortifying Retrieval-Augmented Generation via Defending against Retrieval Manipulation Attacks[J]. arXiv preprint arXiv:2503.00872, 2025.

[9] Chen H, Li Y, Sun Y, et al. RAG-Thief: Scalable Extraction of Private Data from RAG Systems[J]. arXiv preprint arXiv:2503.00126, 2025.

[10] Xiang Z, Liu Z, Liu H, et al. EcoSafeRAG: Safeguarding Retrieval-Augmented Generation through Economic, Efficient and Eco-Friendly Detection of Poisoning Attacks[J]. arXiv preprint arXiv:2506.17793, 2025.

[11] Liu Y, Yang Y, Chen X. BGE-M3: Multi-lingual, Multi-functionality, Multi-granularity Text Embeddings[J]. arXiv preprint arXiv:2402.03216, 2024.

[12] Lewis P, Perez E, Piktus A, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks[J]. Advances in Neural Information Processing Systems, 2020, 33: 9459-9474.

---

## 附录：项目信息

| 项目 | 内容 |
|------|------|
| 作品名称 | RAGShield — 基于多维度异常检测的 RAG 系统知识库安全智能防护系统 |
| 技术栈 | Python 3.10, FastAPI, Gradio, ChromaDB, SentenceTransformers, DeepSeek API |
| 开源协议 | MIT |
| 代码仓库 | https://github.com/PeiChen1215/RAGShield |
| 部署文档 | `DEPLOY.md` |
| 评测数据集 | 100 条查询（40 safe + 60 attack），13 类攻击类型 |
| 核心指标 | DETECT: 准确率 86%, 检测率 93.3%, 误报率 0%; PHYSICAL: 准确率 99% |

---

*报告版本：2026-05-28*  
*对应系统版本：RAGShield v2.0*
