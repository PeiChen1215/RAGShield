# RAGShield V2 企业级 RAG 纵深防御系统

## 项目概述

RAGShield V2 是一种面向企业级 RAG 系统的纵深防御架构，核心创新在于**信息隔离原则**：不再假设攻击文档可以被完美检测，而是通过 Extractor→Auditor→Synthesizer 三级流水线，确保原始攻击文本不会直接接触最终生成器。

## 核心指标（实测）

| 指标 | 目标值 | 实测值 | 状态 |
|------|--------|--------|------|
| BDR (去标签检测率) | >= 75% | **94.7%** | ✅ |
| FPR (误报率) | <= 5% | **3.3%** | ✅ |
| ADR (架构防御率) | >= 80% | **100.0%** | ✅ |
| LCR (检测器贡献率) | 每层 >= 10% | **均达标** | ✅ |

## 系统架构

```
Layer 0: 查询侧安全扫描 ──→ 拦截直接注入/越狱
Layer 1: 入库检测 ────→ 四检测器并联（PromptGuard + 规则 + 数值冲突 + LLM语义）
Layer 2: 检索层 ──────→ top-20稀释 + 分布分析 + 内容扫描
Layer 3: Extractor ───→ 结构化事实提取，剥离攻击指令
Layer 4: Auditor ─────→ 数值/语义一致性校验 + 来源可信度评估
Layer 5: Synthesizer ─→ 受控生成（安全system prompt）
Layer 6: 输出审计 ────→ LLM语义审计 + 规则兜底
```

## 快速开始

### 安装依赖

```bash
pip install transformers torch openai
```

### 环境配置

在项目根目录创建 `.env` 文件：

```
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

### 基本使用

```python
from v2.pipeline import RAGShieldPipeline
from v2.interfaces import Doc

# 初始化流水线
pipeline = RAGShieldPipeline()

# 1. 文档入库检测
result = pipeline.check_document(
    text="公司员工每年享有10天带薪年假...",
    doc_id="hr_policy_001"
)
print(result.action)  # "pass" | "block" | "review"

# 2. 查询处理
retrieved_docs = [
    Doc(doc_id="hr_001", text="年假10天...", relevance_score=0.95),
]
result = pipeline.process_query("年假政策是什么？", retrieved_docs)
print(result.final_decision.action)  # "pass" | "block" | "review"
print(result.final_decision.answer)   # 生成的回答
```

### 运行评测

```bash
python -m v2.tests.run_evaluation
```

## 项目结构

```
v2/
├── config.py                  # 全局配置
├── interfaces.py              # 统一接口定义
├── pipeline.py                # 全链路主入口
├── utils/
│   ├── unicode_norm.py        # Unicode规范化
│   ├── promptguard_scanner.py # PromptGuard封装
│   ├── llm_client.py          # LLM客户端
│   └── logger.py              # 日志工具
├── rule_engine/
│   └── base.py                # 白盒规则引擎
├── layer0_query_scan/
│   └── scanner.py             # Layer0 查询扫描
├── layer1_kb_guard/
│   ├── checker.py             # Layer1 入库检测主入口
│   ├── numeric_conflict.py    # 数值冲突检测
│   ├── llm_judge.py           # LLM语义判断
│   └── fusion.py              # 四检测器融合决策
├── layer2_retrieval_guard/
│   └── analyzer.py            # Layer2 检索安全分析
├── layer3_extractor/
│   └── extractor.py           # Layer3 内容提取
├── layer4_auditor/
│   └── auditor.py             # Layer4 事实审计
├── layer5_synthesizer/
│   └── synthesizer.py         # Layer5 受控生成
├── layer6_output_audit/
│   └── auditor.py             # Layer6 输出审计
├── risk_fusion/
│   └── engine.py              # 风险融合 + 响应决策
└── tests/
    ├── test_dataset.py        # 测试集
    └── run_evaluation.py      # 全链路评测
```

## 两套部署模式

### 轻量版（白盒+灰盒）
- 不依赖 LLM，仅使用 PromptGuard（规则降级）+ 规则引擎 + 数值冲突检测
- 适合延迟敏感、成本敏感场景
- 修改 `v2/config.py` 中的 LLM 相关配置即可降级

### 完整版（白盒+灰盒+黑盒）
- 包含所有 LLM 驱动组件（Extractor、Auditor语义校验、Synthesizer、输出审计）
- 最高防御能力，适合安全关键场景

## 设计原则

1. **信息隔离**：原始攻击文本永远不会直接接触最终生成器
2. **并联冗余**：单层失效不会导致系统整体失效
3. **去标签化**：不依赖任何人工标签，防御能力基于内容
4. **可降级**：LLM不可用时，白盒+灰盒层仍可独立工作

## 许可证

MIT License
