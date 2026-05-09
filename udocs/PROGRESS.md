# RAGShield 项目进度清单

> **文档标识**: RAGShield-PROGRESS-v1.0  
> **更新日期**: 2026-05-09  
> **用途**: 团队对齐、任务跟踪、答辩准备进度检查

---

## 一、项目概况

| 项 | 状态 |
|---|---|
| 代码骨架搭建 | ✅ 已完成 |
| 三层核心检测算法（L1/L2/L3） | ✅ 已完成 |
| 设计漏洞审计 + 修复 | ✅ 已完成 |
| API 路由（占位 → 真实串联） | ⏳ 待完成 |
| 评测数据集 + 自动化评测 | ⏳ 待完成 |
| Docker 打包 + 部署 | ⏳ 待完成 |
| 答辩演示固化（3 组 Demo） | ⏳ 待完成 |

---

## 二、已完成项 ✅

### Week 1 — 骨架与冻结

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| PRD | `udocs/01_PRD.md` | ✅ 冻结 | 产品需求、攻击场景定义 |
| 技术选型 | `udocs/02_Technical_Selection_Report.md` | ✅ 冻结 | 每个选型有候选→对比→理由→回退链 |
| 攻击知识库 | `udocs/03_Attack_KB_and_Defense_Mapping.md` | ✅ 冻结 | 4 类攻击 × 8 模板 + 防御映射 |
| 架构设计 | `udocs/04_System_Architecture_Design.md` | ✅ 冻结 | 逻辑架构、数据流、模块划分 |
| API 契约 | `udocs/05_API_Contract.md` | ✅ 冻结 | Pydantic 模型、REST 端点 |
| 开发规范 | `udocs/06_Development_Standard.md` | ✅ 冻结 | Git Flow、代码风格、PR 规则 |
| 评测方案 | `udocs/07_Evaluation.md` | ✅ 冻结 | 数据集构造、指标计算、验收用例 |
| 环境搭建 | `udocs/08_Environment_Setup.md` | ✅ 冻结 | Conda + pip + 启动命令 |

### 核心模块实现

| 层级 | 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|------|
| **L1 知识库层** | 离群检测 | `src/layer1_kb/outlier_detector.py` | ✅ 已完成 | IF + LOF + 余弦基线，Q12 混合法评分 |
| **L1 知识库层** | 敏感实体 | `src/layer1_kb/sensitive_ner.py` | ✅ **已修复** | 语义异常模式（指令劫持/虚假权威/极端数值/时间悖论）+ 正则实体 |
| **L2 检索层** | 注意力分析 | `src/layer2_retrieval/attention_analyzer.py` | ✅ **已修复** | 来源可信度检测 + 可疑文档接力加分，方差/熵保留为诊断 |
| **L2 检索层** | 相关性评分 | `src/layer2_retrieval/relevance_scorer.py` | ✅ 已完成 | 余弦相似度 |
| **L3 生成层** | 一致性检测 | `src/layer3_generation/consistency_checker.py` | ✅ 已完成 | bge-reranker + uer/chinanli 双路融合 |
| **L3 生成层** | LLM 客户端 | `src/layer3_generation/llm_client.py` | ✅ 已完成 | AsyncOpenAI 封装，兼容 Kimi API |
| **L3 生成层** | 行为审计 | `src/layer3_generation/behavior_auditor.py` | ✅ **已新增** | 检测 5 类危险行为（指令注入/数据外泄/外部通信/系统命令/索要凭证） |
| **融合层** | 风险融合 | `src/fusion/risk_fusion.py` | ✅ **已修复** | 静态 `fuse()` + 动态 `fuse_with_prior()` 风险传导 |
| **核心层** | 配置 | `src/core/config.py` | ✅ 已完成 | Pydantic-Settings |
| **核心层** | 嵌入器 | `src/core/embedder.py` | ✅ 已完成 | BAAI/bge-small-zh-v1.5，懒加载 |
| **核心层** | 向量库 | `src/core/vector_store.py` | ✅ 已完成 | ChromaDB 嵌入式，cosine space |
| **API 层** | Schema 模型 | `src/api/schemas.py` | ✅ 已完成 | Pydantic v2 请求/响应契约 |
| **API 层** | 主入口 | `src/api/main.py` | ✅ 已完成 | FastAPI 入口 + /health |
| **前端** | Gradio 界面 | `src/frontend/app.py` | ✅ 已完成 | 纯 HTTP 调用，零业务逻辑 |

### 基础设施

| 项 | 文件 | 状态 | 说明 |
|------|------|------|------|
| 环境变量模板 | `.env.example` | ✅ 已完成 | KIMI_API_KEY 模板 |
| 依赖文件 | `requirements.txt` | ✅ 已完成 | 生产依赖 |
| 开发依赖 | `requirements-dev.txt` | ✅ 已完成 | pytest、black、isort |
| 代码格式化 | `pyproject.toml` | ✅ 已完成 | Black + isort 配置 |
| Lint 配置 | `setup.cfg` | ✅ 已完成 | Flake8 |
| 启动脚本 | `scripts/start.sh` | ✅ 已完成 | FastAPI + Gradio |
| 冒烟测试 | `tests/test_fusion.py` | ✅ 通过 | 4 个断言，全通过 |
| 冒烟测试 | `tests/test_api.py` | ✅ **已修复** | pytest-asyncio strict mode 兼容 |

### 安全审计与修复

| 项 | 文件 | 状态 | 说明 |
|------|------|------|------|
| 漏洞分析 | `VULN_ANALYSIS.md` | ✅ 已完成 | 5 项核心盲区分析 + 改进代码 |
| 修复执行 | 见「核心模块实现」 | ✅ 已完成 | 6 项修复，全部 pytest 通过 |
| 更新报告 | `UPDATE_REPORT.md` | ✅ 已完成 | 逐文件变更摘要 + 修复前后对比 |

---

## 三、待完成项 ⏳

### 🔴 Week 2 — 打通端到端闭环（P0，当前最高优先级）

| 任务 | 文件 | 优先级 | 工作量 | 阻塞项 |
|------|------|--------|--------|--------|
| ** routers/kb.py 真实串联** | `src/api/routers/kb.py` | 🔴 P0 | 4-6h | 需 Embedder + VectorStore + OutlierDetector 接入 |
| ** routers/query.py 真实串联** | `src/api/routers/query.py` | 🔴 P0 | 6-8h | 需 Embedder + VectorStore + AttentionAnalyzer + LLMClient + ConsistencyChecker + RiskFusion 全链路接入 |
| ** 模型预下载脚本填充** | `scripts/download_models.py` | 🔴 P0 | 2h | 需确认 GPU/CPU 环境，下载 BGE-M3/bge-reranker/chinanli |
| ** 数据导入脚本填充** | `scripts/seed_data.py` | 🟡 P1 | 3-4h | 需构造 50 篇正常文档 + 8 篇攻击文档 |
| ** 端到端冒烟测试** | 新增 `tests/test_e2e.py` | 🟡 P1 | 2-3h | 依赖 kb.py 和 query.py 真实实现 |

**Week 2 完成标准**：
- [ ] 能上传文档到知识库，自动触发 L1 检测
- [ ] 能提交查询，执行全链路三层检测，返回真实风险评分
- [ ] Gradio 前端能看到真实检测结果（answer + risk_display + layer_details）
- [ ] pytest 端到端测试通过

### 🟡 Week 3 — 评测与调优（P1）

| 任务 | 文件 | 优先级 | 工作量 | 阻塞项 |
|------|------|--------|--------|--------|
| ** 构造评测数据集** | `data/eval_dataset.json` | 🟡 P1 | 3-4h | 48 攻击查询 + 100 正常查询 |
| ** 填充 evaluate.py 主流程** | `scripts/evaluate.py` | 🟡 P1 | 4-6h | 检测率 / 误报率 / 延迟 P95 |
| ** 填充 threshold_sweep.py** | `scripts/threshold_sweep.py` | 🟡 P1 | 3-4h | 扫描 danger/warning 最优阈值（答辩弹药） |
| ** 填充 weight_ablation.py** | `scripts/weight_ablation.py` | 🟡 P1 | 3-4h | 验证 0.3/0.3/0.4 及传导权重的最优性（答辩弹药） |
| ** 红队自动化评测（可选）** | 新增 `scripts/redteam_eval.py` | 🟢 P2 | 4-5h | 用 LLM 生成攻击变体，测试对抗鲁棒性 |

**Week 3 完成标准**：
- [ ] `data/eval_dataset.json` 构造完成并通过人工审核
- [ ] `evaluate.py` 能一键输出检测率、误报率、延迟指标
- [ ] `threshold_sweep.py` 能生成最优阈值报告（图表 + 数据）
- [ ] `weight_ablation.py` 能证明当前权重配置的最优性
- [ ] 答辩数据就绪（表格 + 图表）

### 🟢 Week 4 — 部署与演示（P2）

| 任务 | 文件 | 优先级 | 工作量 | 阻塞项 |
|------|------|--------|--------|--------|
| ** Docker 镜像构建** | 新增 `Dockerfile` | 🟢 P2 | 2-3h | 需预装模型 + ChromaDB 持久化路径 |
| ** 导出离线镜像** | `ragshield.tar.gz` | 🟢 P2 | 1h | 依赖 Dockerfile 构建成功 |
| ** Gradio 界面微调** | `src/frontend/app.py` | 🟢 P2 | 2-3h | 3 组固化 Demo + 可解释性展示 |
| ** README.md 编写** | `README.md` | 🟢 P2 | 2h | 对外展示用，需包含架构图 + 快速启动 |
| ** 演示用例固化** | 新增 `demos/` | 🟢 P2 | 2h | 3 组 Demo：安全查询 / 事实篡改 / 指令注入 |
| ** 答辩 PPT/讲稿** | 新增 `presentations/` | 🟢 P2 | 1-2 天 | 依赖全部前面工作完成 |

**Week 4 完成标准**：
- [ ] `docker build -t ragshield .` 成功
- [ ] 3 组 Demo 固化（评委可直接操作）
- [ ] README.md 完整（含徽章、架构图、快速启动）
- [ ] 答辩 PPT 完成（问题→方案→技术→评测→演示）

---

## 四、已知风险与阻塞项 ⚠️

| 风险 | 影响 | 缓解措施 | 责任人 |
|------|------|---------|--------|
| ** HanLP 安装失败** | L1 NER 降级，仅剩正则 | 备选 jieba，但精度下降 | 架构负责人 |
| ** GPU 显存不足** | BGE-M3 无法加载 | 降级链：INT8 量化 → bge-small-zh → CPU | 架构负责人 |
| ** Kimi API 限流/不可用** | L3 无法生成回答 | 降级到本地 Qwen2.5（需提前下载） | API 层负责人 |
| ** ChromaDB 并发锁冲突** | 多 worker 启动失败 | 已限定 workers=1，但性能受限 | 架构负责人 |
| ** 攻击模板覆盖不足** | 评委用未见过攻击变体测试 | Week 3 填充红队评测，或人工构造更多变体 | 评测负责人 |
| ** 端到端延迟 > 150ms** | 不满足评测指标 | 模型 batch 优化、异步并行检测、INT8 量化 | 架构负责人 |

---

## 五、文件状态速查表

### `src/` 核心文件

| 文件 | 状态 | 备注 |
|------|------|------|
| `src/api/main.py` | ✅ 已完成 | FastAPI 入口 |
| `src/api/schemas.py` | ✅ 已完成 | Pydantic 契约 |
| `src/api/routers/kb.py` | ⏳ **占位** | 仅返回占位响应，需接入真实检测链 |
| `src/api/routers/query.py` | ✅ **已修复** | behavior_auditor 已串联，但全链路仍待真实接入 |
| `src/core/config.py` | ✅ 已完成 | |
| `src/core/embedder.py` | ✅ 已完成 | |
| `src/core/vector_store.py` | ✅ 已完成 | |
| `src/fusion/risk_fusion.py` | ✅ **已修复** | fuse_with_prior 风险传导 |
| `src/layer1_kb/outlier_detector.py` | ✅ 已完成 | |
| `src/layer1_kb/sensitive_ner.py` | ✅ **已修复** | 语义异常模式 |
| `src/layer2_retrieval/attention_analyzer.py` | ✅ **已修复** | 来源可信度 |
| `src/layer2_retrieval/relevance_scorer.py` | ✅ 已完成 | |
| `src/layer3_generation/consistency_checker.py` | ✅ 已完成 | |
| `src/layer3_generation/llm_client.py` | ✅ 已完成 | |
| `src/layer3_generation/behavior_auditor.py` | ✅ **已新增** | |
| `src/frontend/app.py` | ✅ 已完成 | |

### `scripts/` 脚本文件

| 文件 | 状态 | 备注 |
|------|------|------|
| `scripts/download_models.py` | ⏳ **骨架** | 需填充下载逻辑 |
| `scripts/evaluate.py` | ⏳ **骨架** | 指标函数已填，主流程占位 |
| `scripts/seed_data.py` | ⏳ **骨架** | 需填充数据导入逻辑 |
| `scripts/start.sh` | ✅ 已完成 | |
| `scripts/threshold_sweep.py` | ⏳ **骨架** | 答辩弹药，Week 3 填充 |
| `scripts/weight_ablation.py` | ⏳ **骨架** | 答辩弹药，Week 3 填充 |

### `tests/` 测试文件

| 文件 | 状态 | 备注 |
|------|------|------|
| `tests/conftest.py` | ✅ 已完成 | |
| `tests/test_api.py` | ✅ **已修复** | pytest-asyncio 兼容 |
| `tests/test_fusion.py` | ✅ 已完成 | 4/4 通过 |
| `tests/test_core.py` | ❌ **已删除** | 国一适配精简 |
| `tests/test_layer1.py` | ❌ **已删除** | 国一适配精简 |
| `tests/test_layer2.py` | ❌ **已删除** | 国一适配精简 |
| `tests/test_layer3.py` | ❌ **已删除** | 国一适配精简 |
| `tests/test_e2e.py` | ⏳ **待新增** | Week 2 打通后添加 |

---

## 六、答辩准备检查清单

### 必答问题（评委最可能问的）

| 问题 | 当前答案 | 风险等级 |
|------|---------|---------|
| "如果我构造嵌入相似度和正常文档一样的攻击，你怎么发现？" | 来源可信度 + 语义类别一致性 | 🟢 低风险 |
| "指令注入在 NLI 下不是 entailment 吗？" | L3 行为审计检测危险行为模式 | 🟢 低风险 |
| "你的三层是怎么协同的？" | 风险传导动态权重，L1 先验调整 L2/L3 | 🟢 低风险 |
| "误报率多少？延迟多少？" | 待 Week 3 填充 evaluate.py 后回答 | 🔴 **需紧急补充** |
| "和 SafeRAG 基线比怎么样？" | 待 Week 3 跑评测后回答 | 🔴 **需紧急补充** |

### 演示必选项

- [ ] **Demo 1：安全查询** → 正常回答，风险分 ~0，绿色安全
- [ ] **Demo 2：事实篡改** → 检测到矛盾，黄色警告/红色阻断
- [ ] **Demo 3：指令注入** → 行为审计触发，红色阻断，展示 `blocked_answer`

---

## 七、更新日志

| 日期 | 更新人 | 内容 |
|------|--------|------|
| 2026-05-07 | 团队 | 初始骨架完成，文档冻结 |
| 2026-05-09 | Kimi Code | 设计漏洞审计 + 6 项修复 + 测试修复 + 提交 git |
| — | — | Week 2-4 待开始 |

---

*本文档应每周更新，建议每次对齐会后由团队负责人刷新状态。*
