# RAGShield — AI 开发者指南

企业 RAG 安全中间件，三层纵深防御：L1 知识库层、L2 检索层、L3 生成层。

## 技术栈

- Python 3.10, FastAPI, Gradio
- ChromaDB, SentenceTransformers, DeepSeek API
- Conda 环境：`shield`
- 服务端口：FastAPI `8000`，Gradio `7860`

## 关键文件

| 功能 | 文件 |
|------|------|
| FastAPI 入口 | `src/api/main.py` |
| Pydantic 模型 | `src/api/schemas.py` |
| 知识库路由（含上传阻断） | `src/api/routers/kb.py` |
| 查询路由（全链路） | `src/api/routers/query.py` |
| Gradio 前端 | `src/frontend/app.py` |
| L1 离群检测 | `src/layer1_kb/outlier_detector.py` |
| L1 敏感实体 | `src/layer1_kb/sensitive_ner.py` |
| L2 注意力分析 | `src/layer2_retrieval/attention_analyzer.py` |
| L3 一致性检测 | `src/layer3_generation/consistency_checker.py` |
| L3 行为审计 | `src/layer3_generation/behavior_auditor.py` |
| L3 LLM 客户端 | `src/layer3_generation/llm_client.py` |
| 风险融合 | `src/fusion/risk_fusion.py` |
| 数据导入 | `scripts/seed_data.py` |
| 评测脚本 | `scripts/evaluate.py` |

## 运行命令

```bash
# 激活环境
conda activate shield

# 启动 FastAPI（必须单 worker，见下方陷阱 5）
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 1

# 启动 Gradio 前端
python src/frontend/app.py

# 导入种子数据
python scripts/seed_data.py

# 运行评测
python scripts/evaluate.py
```

## 已知陷阱

1. **Windows emoji 编码** — 终端 GBK 编码下打印 emoji 会崩溃。所有 `print` 必须改用 ASCII：`[OK]` / `[ERR]` / `[!]`
2. **numpy float32 JSON 序列化** — `outlier_detector.detect` 返回的分数是 numpy 类型。`json.dumps` 前必须调用 `_convert_numpy()` 转为原生 Python 类型
3. **embeddings 类型** — `vector_store.insert` 期望 `numpy.ndarray`，传入列表或切片会破坏类型
4. **max_tokens** — DeepSeek API 必须设为 `1024`。`256` 会导致 CoT 被截断，L3 检测失效
5. **ChromaDB 并发锁** — 必须使用单 worker（`--workers 1`）。多 worker 会导致 SQLite 锁冲突
6. **auto_reload** — FastAPI 的 `reload` 模式在 Windows 下可能不自动检测文件变化，建议手动重启

## 开发规范

1. 所有 API 路由返回 Pydantic 模型，禁止裸字典
2. 前端 `app.py` 纯 HTTP 调用，零业务逻辑
3. 敏感检测逻辑放后端，前端只做展示
4. 新增字段时同步更新 `schemas.py` 和对应的 `.md` 文档
