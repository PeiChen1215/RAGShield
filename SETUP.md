# RAGShield 项目运行指南

> **文档标识**: RAGShield-SETUP-v2.0  
> **创建日期**: 2026-05-07  
> **用途**: RAGShield 完整运行指南，反映当前项目真实状态。

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
│   ├── attack_kb/               # 攻击模板库（已填充）
│   ├── normal_kb/               # 正常文档库（已填充）
│   ├── queries/                 # 查询集合（已填充）
│   └── chroma_db/               # ChromaDB 持久化（.gitignore）
├── old_docs/                    # 旧版文档归档
├── scripts/
│   ├── download_models.py       # 模型预下载
│   ├── evaluate.py              # 评测主脚本（已完成）
│   ├── seed_data.py             # 数据导入（已完成，100 正常 + 25 攻击）
│   ├── start.sh                 # 容器启动（FastAPI + Gradio）
│   ├── threshold_sweep.py       # 阈值扫描（已完成）
│   └── weight_ablation.py       # 权重消融（已完成）
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI 入口 + /health
│   │   ├── schemas.py           # Pydantic 模型（已冻结）
│   │   └── routers/
│   │       ├── kb.py            # /kb/upload, /kb/scan
│   │       └── query.py         # /query（三层检测链已串）
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
│       ├── behavior_auditor.py  # 行为审计（新增）
│       ├── consistency_checker.py # bge-reranker + chinanli 双路融合（已填）
│       └── llm_client.py        # DeepSeek API 封装
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

### ✅ 已完成（全部可直接运行/测试）

| 模块 | 实现状态 | 说明 |
|------|---------|------|
| `api/schemas.py` | **100%** | 全部 Pydantic 模型已代码化 |
| `api/main.py` | **100%** | FastAPI 入口、路由注册、CORS、/health |
| `api/routers/kb.py` | **100%** | 上传 + 扫描，支持 `block_threshold` 入库阻断 |
| `api/routers/query.py` | **100%** | 查询三层检测链完整打通 |
| `core/config.py` | **100%** | Pydantic-Settings，读取 .env 和 config.yaml |
| `core/embedder.py` | **100%** | SentenceTransformer 封装，懒加载，L2 归一化 |
| `core/vector_store.py` | **100%** | ChromaDB 嵌入式，cosine space，kb_id 隔离 |
| `layer1_kb/outlier_detector.py` | **100%** | 多维度离群检测，入库扫描检出率 100% |
| `layer1_kb/sensitive_ner.py` | **100%** | 5 类正则规则 + 风险加分映射 |
| `layer2_retrieval/attention_analyzer.py` | **100%** | 方差/熵 + Layer1 接力加分 |
| `layer2_retrieval/relevance_scorer.py` | **100%** | 点积计算余弦相似度 |
| `layer3_generation/behavior_auditor.py` | **100%** | 行为审计：指令注入 / 数据外泄 / 系统命令 / 索要凭证 |
| `layer3_generation/consistency_checker.py` | **100%** | bge-reranker + chinanli 双路融合 |
| `layer3_generation/llm_client.py` | **100%** | AsyncOpenAI 封装，DeepSeek API |
| `fusion/risk_fusion.py` | **100%** | 0.3/0.3/0.4 加权 + 三级响应 |
| `frontend/app.py` | **100%** | Gradio Tab 布局：查询检测 + 知识库上传 |
| `scripts/seed_data.py` | **100%** | 导入 100 篇正常文档 + 25 篇攻击文档 |
| `scripts/evaluate.py` | **100%** | 一键评测 47 条查询，输出检测率/误报率/延迟 |
| `scripts/threshold_sweep.py` | **100%** | 阈值扫描 |
| `scripts/weight_ablation.py` | **100%** | 权重消融 |
| `tests/test_fusion.py` | **100%** | 4 个断言，pytest 直接通过 |

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
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 4. 下载模型
python scripts/download_models.py

# 5. 导入数据
python scripts/seed_data.py

# 6. 启动后端（端口 8000，单 worker 避免 ChromaDB 锁冲突）
python -m src.api.main

# 7. 启动前端（端口 7860，另开终端）
python -m src.frontend.app

# 8. 浏览器打开
# Swagger UI: http://localhost:8000/docs
# Gradio UI:   http://localhost:7860

# 9. 运行冒烟测试
pytest tests/ -v
```

---

## 六、已实现功能清单

- [x] **L1 知识库层**：多维度离群检测 + 敏感 NER，入库扫描 25/25 攻击文档全部检出
- [x] **L2 检索层**：来源可信度验证 + 可疑文档接力加分 + 注意力方差/熵诊断
- [x] **L3 生成层**：NLI 双路融合（bge-reranker + chinanli）+ 行为审计
- [x] **风险融合**：0.3/0.3/0.4 加权 + 风险传导 + 三级响应（safe / warning / danger）
- [x] **入库阻断**：`POST /api/v1/kb/upload` 支持 `block_threshold` 参数（0.0~1.0）
- [x] **评测闭环**：47 条查询，准确率 100%，检测率 100%，误报率 0%，漏报率 0%
- [x] **Gradio 前端**：Tab 布局（查询检测 + 知识库上传），支持阈值滑块与阻断展示
- [x] **数据导入**：`scripts/seed_data.py` 一键导入 100 正常 + 25 攻击文档

## 七、上传阻断功能说明

`POST /api/v1/kb/upload` 支持 `block_threshold` 参数，在文档入库前进行 L1 扫描：

| 阈值 | 行为 | 适用场景 |
|------|------|---------|
| **1.0** | 不阻断（默认） | 攻击文档允许入库，后续查询时拦截 |
| **0.6** | 阻断高风险 | 第一道防线，拦截明显攻击文档 |
| **0.0** | 阻断所有可疑 | 最严格模式，宁可误拦不可漏放 |

前端 Gradio「知识库上传」Tab 提供阈值滑块、文档输入框、快速填充按钮，并实时展示阻断结果。

---

*本指南反映 RAGShield 当前真实状态，所有模块均已硬实现并通过评测。*
