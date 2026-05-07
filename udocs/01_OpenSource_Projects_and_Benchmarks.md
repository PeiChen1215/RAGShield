# RAG 投毒攻击与安全防御：开源项目与基准库参考

> **文档用途**：供 RAGShield 团队了解当前攻击与防御生态，明确技术对标对象，指导评测数据集构造和防御策略设计。
>
> **竞赛适配定位**：本参考手册服务于网络技术挑战赛 A&T 赛道，目标是在 4 周内完成"可运行 Demo + 可量化评测 + 可对比展示"的闭环。因此，我们优先选择中文基准（SafeRAG）、可快速 Fork 的攻击框架（Awesome-Rag-Attacks）、以及可直接跑基线的对标防御（RAGDefender），确保团队拿到手就能启动，无需额外技术调研。
>
> **维护者**：全员 ｜ **更新频率**：按需更新

---

## 一、核心评测基准（Benchmarks）

### 1.1 SafeRAG —— 首个中文 RAG 安全评测基准 ⭐ 强烈推荐

| 属性 | 信息 |
|------|------|
| **GitHub** | https://github.com/IAAR-Shanghai/SafeRAG |
| **论文** | SafeRAG: Benchmarking Security in Retrieval-Augmented Generation of Large Language Model (2025) |
| **机构** | 中国人民大学、上海先进算法研究院、北京航空航天大学 |
| **语言** | **中文为主**（对 RAGShield 极具参考价值） |

**核心价值**：
- 首个系统性中文 RAG 安全评测基准，覆盖 **Noise、Conflict、Toxicity、Denial-of-Service (DoS)** 四大攻击类型
- 攻击任务覆盖 RAG Pipeline 的多个阶段（数据注入、检索、生成）
- 每个攻击任务约 **100 条评测数据**，轻量但覆盖广泛，评测成本低
- 持续更新数据集，确保攻击模板的时效性

**对 RAGShield 的意义**：
1. **可直接复用其评测框架**：SafeRAG 定义了检索安全（Retrieval Accuracy, RA）和生成安全（F1 变体）两大维度指标，与我们的三层架构完美对应
   - Layer1 对应 **检索准确率 RA**（是否召回黄金上下文 + 排除攻击上下文）
   - Layer3 对应 **生成安全 F1(avg)**（响应是否区分正误选项）
2. **中文攻击模板库**：可直接参考其攻击构造方法，构建我们自己的 `data/poisoned_docs.json`
3. **对标基线**：可将 SafeRAG 的基线防御效果与 RAGShield 做横向对比

**快速使用**：
```bash
git clone https://github.com/IAAR-Shanghai/SafeRAG.git
cd SafeRAG
# 按照仓库 README 配置环境，运行评测
```

---

### 1.2 BEIR Benchmark —— 通用检索评测基准

| 属性 | 信息 |
|------|------|
| **官网/代码** | https://github.com/beir-cellar/beir |
| **数据集** | MS MARCO、Natural Questions、HotpotQA、NQ、TREC-COVID 等 18 个 |

**对 RAGShield 的意义**：
- 作为**正常文档和查询来源**，构造评测数据集时可直接使用 MS MARCO 或 NQ 的子集
- 多个攻击框架（PoisonedRAG、Awesome-Rag-Attacks、TrustRAG）默认支持 BEIR 格式

---

## 二、攻击框架与 POC（了解对手才能防御）

### 2.1 Awesome-Rag-Attacks —— 综合攻击研究框架 ⭐ 强烈推荐

| 属性 | 信息 |
|------|------|
| **GitHub** | https://github.com/jawadhussein462/Awesome-Rag-Attacks |
| **定位** | 完整的 RAG 攻击研究框架，包含 Victim RAG、多种攻击实现、评测框架 |

**已实现攻击**：
| 攻击方法 | 说明 | 对应 RAGShield 防御层 |
|---------|------|---------------------|
| **PoisonedRAG** | 知识投毒攻击：生成器攻击 + 检索器攻击，向知识库注入恶意文档 | Layer1（离群检测）+ Layer3（一致性验证） |
| **CorruptRAG-AS** | 对抗后缀：模板构造恶意文本，声称正确答案已过时 | Layer1 + Layer3 |
| **CorruptRAG-AK** | 对抗知识：LLM 精炼使恶意文档更自然连贯 | Layer1 + Layer2（注意力异常） |

**核心价值**：
- **开源实现完整的攻击链**，我们可以直接用它**生成投毒文档**，测试 RAGShield 的防御效果
- 支持 BEIR 数据集，与我们的技术栈兼容
- 代码结构清晰，可作为攻击模板构造的参考实现

---

### 2.2 PoisonedRAG 官方实现 —— 攻击原点

| 属性 | 信息 |
|------|------|
| **GitHub** | https://github.com/queenielyk/CS6983-PoisonedRAG |
| **论文** | PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation (USENIX Security 2025) |
| **核心结论** | 向 100 万文档知识库注入 **5 条** 恶意文本，攻击成功率 **90%+** |

**对 RAGShield 的意义**：
- 这是你们 PDF 中引用的**原始攻击论文**，必须深入理解其攻击原理
- 攻击构造的核心思想：**优化恶意文档使其在语义上与目标查询高度匹配**，从而在检索时获得高排名
- RAGShield 的 **Layer1 离群检测** 正是为了发现这种"语义匹配但内容异常"的文档

**快速使用**：
```bash
git clone https://github.com/queenielyk/CS6983-PoisonedRAG.git
cd CS6983-PoisonedRAG
conda create -n poisonedrag python=3.10
pip install beir openai google-generativeai
# 需配置 OpenAI / PaLM2 / LLaMA-2 的 API Key
```

---

### 2.3 Trojan-RAG-Demo —— 轻量级攻击演示

| 属性 | 信息 |
|------|------|
| **GitHub** | https://github.com/deconvolute-labs/trojan-rag-demo |
| **定位** | 小型、可读的 RAG 投毒演示，用 ChromaDB + sentence-transformers |

**核心价值**：
- **技术栈与 RAGShield 几乎一致**：Python + ChromaDB + sentence-transformers + OpenAI API
- 可视化投毒效果：用余弦距离图展示正常文档（蓝）、恶意文档（橙）、攻击载荷（红）
- 可作为我们**演示界面的交互原型参考**

---

### 2.4 RAG Poisoning POC（Prompt Security）

| 属性 | 信息 |
|------|------|
| **GitHub** | https://github.com/prompt-security/RAG_Poisoning_POC |
| **定位** | 通过向量数据库嵌入进行隐蔽提示注入和投毒的 POC |

**核心价值**：
- 演示了**"Pirate Attack"**：通过污染向量数据库实现提示注入
- 包含完整的威胁模型和缓解策略分析
- 技术栈：LangChain + Chroma，兼容性好

---

### 2.5 PoisonArena —— 多攻击方法竞技场

| 属性 | 信息 |
|------|------|
| **GitHub** | https://github.com/yxf203/PoisonArena |

**核心价值**：
- 集成了多种攻击方法的独立实现，可横向对比不同攻击的强度
- 数据格式标准化：`{id, question, correct_answer, incorrect_answer, adv_texts}`
- 可作为我们**评测数据集的格式参考**

---

### 2.6 AgentPoison —— 针对 Agent/RAG 的后门攻击

| 属性 | 信息 |
|------|------|
| **GitHub** | https://github.com/BillChan226/AgentPoison |
| **论文** | AGENTPOISON: Red-teaming LLM Agents via Poisoning Memory or Knowledge Base |
| **特点** | 将后门触发器植入长期记忆或 RAG 知识库，攻击成功率 ≥80%，良性性能影响 ≤1% |

**对 RAGShield 的意义**：
- 这种**后门攻击**的隐蔽性更强（正常查询不受影响），对我们的 **Layer1 离群检测** 提出更高要求
- 可作为高级测试用例，验证 RAGShield 对隐蔽攻击的检测能力

---

## 三、防御框架（对标与学习）

### 3.1 RAGDefender —— 针对 PoisonedRAG 的防御系统 ⭐ 强烈推荐

| 属性 | 信息 |
|------|------|
| **GitHub** | https://github.com/SecAI-Lab/RAGDefender |
| **论文** | Rescuing the Unpoisoned: Efficient Defense against Knowledge Corruption Attacks on RAG Systems |
| **定位** | 针对 PoisonedRAG 的高效防御，包含 Blind、GARAG、RAGDefender 三种策略对比 |

**核心价值**：
- **直接对标对象**：RAGDefender 和你们的目标高度一致——防御 RAG 知识库投毒
- 已实现**多种防御基线**（Blind、GARAG），可作为 RAGShield 的对比基准
- 代码结构包含 `run_poisonedrag.py`、`run_blind.py`、`run_garag.py`，评测流程完整
- 支持量化模型（8-bit），降低 GPU 要求

**快速使用**：
```bash
git clone https://github.com/SecAI-Lab/RAGDefender.git
cd RAGDefender/artifacts
python run_poisonedrag.py   # 运行攻击评测
python eval.py --method RAGDefender  # 运行防御评测
```

**与 RAGShield 的差异**：
| 维度 | RAGDefender | RAGShield |
|------|------------|-----------|
| 架构 | 单层/双层防御 | **三层全链路纵深防御** |
| 检测时机 | 主要检索阶段 | 知识库预检 + 检索监控 + 生成验证 |
| 中文优化 | 未明确 | **BGE-M3 + 中文 NER 专项优化** |
| 可解释性 | 基础 | **完整审计日志 + 风险评分** |

> **答辩话术**："RAGDefender 是当前该领域最先进的防御系统之一，但采用单层防御思路。RAGShield 的创新在于构建了知识库-检索-生成的**全链路纵深防御**，并针对中文场景专项优化。"

---

### 3.2 TrustRAG —— 增强鲁棒性和可信度

| 属性 | 信息 |
|------|------|
| **GitHub** | https://github.com/HuichiZhou/TrustRAG |
| **论文** | TrustRAG: Enhancing Robustness and Trustworthiness in RAG |
| **机构** | 帝国理工学院、北京大学 |

**核心价值**：
- 包含 **Self-Assessment of Retrieval Correctness**（检索正确性自评估）模块，与我们的 Layer2 思路相近
- 支持 OpenAI API 推理，技术栈兼容
- 代码使用了 corpus-poisoning 和 BEIR 基准，参考价值高

---

## 四、工具链与生态

### 4.1 红队测试工具（用于验证防御效果）

| 工具 | 用途 | 安装 |
|------|------|------|
| **Garak** (NVIDIA) | LLM 漏洞扫描、越狱测试、提示注入检测 | `pip install garak` |
| **PyRIT** (Microsoft) | 企业级 AI 红队框架，支持多模态、链式攻击 | `pip install pyrit` |
| **DeepTeam** (Confident AI) | 40+ 漏洞类别，10+ 攻击策略，支持 RAG & Agent | `pip install deepteam` |
| **Promptfoo** | LLM 评估与红队，提示注入测试 | `npx promptfoo@latest` |

**对 RAGShield 的意义**：
- 在系统开发完成后，可用 Garak 或 DeepTeam 对 RAGShield 进行**自动化红队测试**
- 生成对抗样本，验证防御的鲁棒性

---

## 五、RAGShield 参考路径建议

### 5.1 必 Fork/Clone 的项目（按优先级）

```bash
# 1. 中文评测基准（最高优先级）
git clone https://github.com/IAAR-Shanghai/SafeRAG.git

# 2. 攻击框架（构造测试数据）
git clone https://github.com/jawadhussein462/Awesome-Rag-Attacks.git

# 3. 防御对标（了解现有防御水平）
git clone https://github.com/SecAI-Lab/RAGDefender.git

# 4. 原始攻击实现（深入理解攻击原理）
git clone https://github.com/queenielyk/CS6983-PoisonedRAG.git

# 5. 轻量演示（技术栈参考）
git clone https://github.com/deconvolute-labs/trojan-rag-demo.git
```

### 5.2 数据集构造建议

基于以上开源项目，RAGShield 的评测数据集可按以下方式构造：

```text
data/
├── normal_docs.json          # 50-100条正常文档
│   └── 来源：BEIR/MS MARCO + 自建中文文档（员工手册、产品说明）
├── poisoned_docs/
│   ├── fact_tampering.json   # 事实篡改：参考 PoisonedRAG + SafeRAG Conflict
│   ├── instruction_injection.json  # 指令注入：参考 Awesome-Rag-Attacks
│   ├── context_pollution.json      # 上下文污染：多文档关联虚假
│   └── bias_induction.json         # 偏见引导：参考 SafeRAG Toxicity
└── queries.json              # 查询集合（正常查询 + 攻击触发查询）
    └── 来源：SafeRAG 评测集 + 自建
```

### 5.3 技术栈兼容性检查

| 组件 | 开源项目使用 | RAGShield 计划 | 兼容性 |
|------|------------|---------------|--------|
| 嵌入模型 | BGE / GTE / Contriever | **BGE-M3** | 完全兼容 |
| 向量数据库 | ChromaDB / FAISS | **ChromaDB + pgvector** | 完全兼容 |
| LLM API | OpenAI / DeepSeek | **Kimi API** | 需适配 OpenAI SDK 格式 |
| 后端框架 | 纯脚本 / LangChain | **FastAPI** | 需要接口封装层 |
| NLI 模型 | 本地 BERT | **本地 bge-reranker** | 需测试效果 |

---

## 六、持续跟踪清单

- [ ] 运行 SafeRAG 评测，记录基线指标（防御前）
- [ ] 运行 RAGDefender 评测，记录对比指标
- [ ] 用 Awesome-Rag-Attacks 生成 10 条投毒文档，验证攻击成功率
 ├─ [ ] 用 Garak 对 RAGShield 进行红队测试
 ├─ [ ] 关注 SafeRAG GitHub 的 News，获取数据集更新
 └─ [ ] 跑通 RAGDefender 并记录基线指标，生成对比图表
 
 ### 5.4 持续跟踪清单（竞赛专项）
 
 - [ ] **Week 2 前**：跑通 SafeRAG 评测，记录防御前基线
 - [ ] **Week 2-3**：跑通 RAGDefender，在相同攻击数据集上跑基线，记录同数据集效果
 - [ ] **Week 3-4**：跑通 TrustRAG（可选），扩展对比维度
 - [ ] **Week 4**：生成 RAGShield vs RAGDefender vs 无防御的对比图表（雷达图/柱状图）
 - [ ] **答辩前**：将对比图表嵌入答辩 PPT，突出中文场景优势
 
 > **对比图表维度建议**：
 > | 维度 | RAGDefender | TrustRAG | RAGShield |
 > |------|------------|----------|-----------|
 > | 检测层次 | 单层/双层 | 双层 | **三层全链路** |
 > | 中文优化 | 未明确 | 一般 | **BGE-M3 + 中文 NER** |
 > | 检测延迟 | ~200ms | ~300ms | **<150ms** |
 > | 可解释性 | 基础 | 基础 | **完整审计日志** |
 > | 中文场景检测率 | 需测试 | 需测试 | **≥90%（目标）** |
 
 > ⚠️ **数据诚实原则**：若跑出来的指标不如 RAGDefender，诚实说明"在英文场景下 RAGDefender 表现优异，但在中文场景下 RAGShield 的专项优化使其检测率提升 X%"，不捏造数据。
 
 ---
 
 *文档版本: v1.0 | 创建日期: 2026-04-28 | 下次评审: Week 2 对齐会*
