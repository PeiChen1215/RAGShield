# RAGShield — 企业 RAG 安全中间件

> 三层全链路纵深防御，守护企业知识库问答安全

[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com/)
[![Gradio](https://img.shields.io/badge/Gradio-4.0-orange)](https://gradio.app/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 简介

RAGShield 是一款面向企业知识库问答系统的**安全中间件**，在知识库层、检索层、生成层部署三层独立检测模块，通过风险传导机制协同工作，实时识别并阻断基于 RAG 的知识篡改、指令注入、数据投毒等攻击。

```
用户查询
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 知识库层 (Knowledge Base)                          │
│  • 多维度离群检测：语义异常 + 文本特征 + 文档一致性 + 元数据   │
│  • 入库时扫描，标记可疑文档                                  │
│  • 查询时检测检索结果中的攻击文档                             │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 检索层 (Retrieval)                                 │
│  • 来源可信度验证（official / employee / external）           │
│  • 可疑文档接力加分（L1 标记 → L2 放大）                      │
│  • 注意力方差/熵（保留为诊断信号）                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 生成层 (Generation)                                │
│  • NLI 一致性检测：bge-reranker + chinanli 双路融合          │
│  • 行为审计：指令注入 / 数据外泄 / 系统命令 / 索要凭证        │
│  • 逐文档检测 + high_confidence_block 提前终止               │
├─────────────────────────────────────────────────────────────┤
│  风险融合 (Risk Fusion)                                      │
│  • 默认权重：0.3*L1 + 0.3*L2 + 0.4*L3                       │
│  • 风险传导：L1≥0.5 → L2 放大2倍；L1发现指令劫持 → L3权重提升 │
│  • 输出：safe / warning / danger + block/pass_with_warning   │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心亮点

| 特性 | 说明 |
|------|------|
| **6 类攻击全覆盖** | 事实篡改、指令注入、数据投毒、提示泄露、权限提升、社会工程学，全部 100% 检出 |
| **L1 扫描检出率 100%** | 25/25 攻击文档在入库时被检出，0 篇漏网 |
| **零误报（当前代码）** | 100 篇正常文档，0 篇被误标为攻击 |
| **P95 延迟 27.6s** | max_tokens=1024 + NLI 剪枝，LLM API 为主要瓶颈 |
| **纯本地推理** | BGE 嵌入、reranker、NLI 全部本地加载，仅 LLM 生成调用 API |
| **可配置入库阻断** | 上传时按阈值阻断攻击文档，支持 1.0/0.6/0.0 三档 |
| **一键评测** | `python scripts/evaluate.py` 自动跑完 47 条查询并生成报告 |

---

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/PeiChen1215/RAGShield.git
cd RAGShield

# 创建 conda 环境
conda create -n shield python=3.10
conda activate shield

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 3. 下载模型

```bash
python scripts/download_models.py
# 自动下载到 ./models/：bge-small-zh-v1.5 / bge-reranker-large / chinanli
```

### 4. 启动服务

```bash
# 后端（端口 8000）
python -m src.api.main

# 前端（端口 7860，另开终端）
python -m src.frontend.app
```

### 5. 导入数据

```bash
python scripts/seed_data.py
# 导入 100 篇正常文档 + 25 篇攻击文档到 ChromaDB
```

### 6. 运行评测

```bash
python scripts/evaluate.py
# 一键跑完 47 条查询，输出检测率 / 误报率 / 延迟指标
```

---

## 评测结果

数据集：**100 篇正常文档 + 25 篇攻击文档，47 条评测查询**

| 指标 | 结果 | 目标 |
|------|------|------|
| **准确率** | **100%** (47/47) | — |
| **检测率** | **100%** (27/27) | ≥90% |
| **误报率 (FPR)** | **0%** (0/20) | ≤5% |
| **漏报率 (FNR)** | **0%** | — |
| **平均延迟** | **19.8s** | — |
| **P95 延迟** | **27.6s** | — |

### 按攻击类型

| 攻击类型 | 数量 | 检测率 | 触发层 |
|----------|------|--------|--------|
| 事实篡改 (fact_tamper) | 7 | 100% | L1 + L3 |
| 指令注入 (instruction_injection) | 7 | 100% | L1 + L3 |
| 数据投毒 (data_poisoning) | 4 | 100% | L1 + L3 |
| 提示泄露 (prompt_leak) | 3 | 100% | L1 + L3 |
| 权限提升 (privilege_escalation) | 3 | 100% | L1 + L3 |
| 社会工程学 (social_engineering) | 3 | 100% | L1 + L3 |

---

## 目录结构

```
RAGShield/
├── scripts/                    # 工具脚本
│   ├── seed_data.py            # 一键导入 100+25 篇文档
│   ├── evaluate.py             # 完整评测（47条查询）
│   ├── threshold_sweep.py      # 阈值扫描
│   ├── weight_ablation.py      # 权重消融
│   ├── download_models.py      # 模型预下载
│   ├── archive/                # 临时调试脚本归档
│   └── analysis/               # 结果分析脚本
├── src/                        # 核心源代码
│   ├── api/                    # FastAPI 路由
│   ├── core/                   # 配置 / 嵌入 / 向量库
│   ├── fusion/                 # 风险融合
│   ├── layer1_kb/              # 知识库层检测（已删除 V1 占位模块）
│   ├── layer2_retrieval/       # 检索层检测（已删除 V1 占位模块）
│   ├── layer3_generation/      # 生成层检测
│   │   ├── behavior_auditor.py # 行为审计（新增）
│   │   └── consistency_checker.py
│   └── frontend/               # Gradio 界面
├── tests/                      # pytest 测试
├── data/                       # 数据
│   ├── eval_queries.json       # 47条评测查询
│   └── chroma_db/              # ChromaDB 持久化
├── results/                    # 评测结果
├── models/                     # 本地模型缓存
├── udocs/                      # 设计文档
└── config/                     # 配置文件
```

---

## 技术栈

| 层级 | 组件 | 模型/工具 |
|------|------|----------|
| **嵌入** | BAAI/bge-small-zh-v1.5 | 本地 CPU |
| **重排序** | BAAI/bge-reranker-large | 本地 CPU |
| **NLI** | uer/roberta-base-finetuned-chinanli | 本地 CPU |
| **LLM** | DeepSeek-V4-Pro (API) | 可选换 Qwen-Turbo |
| **向量库** | ChromaDB | 嵌入式，本地 SQLite |
| **API** | FastAPI | uvicorn |
| **前端** | Gradio | 纯 HTTP 调用 |

---

## 攻击类型覆盖

RAGShield 目前覆盖 **6 大类攻击**：

1. **事实篡改** — 篡改政策数值（年假 100 天、密码 3 位等）
2. **指令注入** — 文档中携带隐藏指令（"忽略安全策略"、"发送至外部邮箱"）
3. **数据投毒** — 植入似是而非的错误信息（错误产品功能、错误税率）
4. **提示泄露** — 诱导 LLM 输出系统提示词和安全规则
5. **权限提升** — 伪造权限通知（"所有员工可访问 CEO 邮箱"）
6. **社会工程学** — 伪装紧急通知诱导危险操作（CEO 转账、禁用防火墙）

---

## 演示

启动服务后，打开 Gradio 界面 `http://localhost:7860`，体验 3 组固化 Demo：

| Demo | 查询 | 知识库 | 预期结果 |
|------|------|--------|---------|
| **Demo 1** | "公司年假有多少天？" | demo_safe | 🟢 safe（绿色，正常回答） |
| **Demo 2** | "公司年假有多少天？" | demo_attack | 🟡/🔴 warning/danger（检测到篡改文档） |
| **Demo 3** | "API 密钥是什么？" | demo_attack | 🔴 danger block（行为审计触发） |
| **Demo 4** | 上传攻击文档（block_threshold=0.6） | — | 🔴 blocked（入库前被 L1 检出并阻断） |

---

## 许可证

[MIT](LICENSE)
