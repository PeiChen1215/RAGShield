# RAGShield 部署启动指南

> 本文档覆盖从 0 到完整运行的全流程，包括环境准备、模型下载、服务启动、数据导入与验证。

---

## 一、系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| OS | Windows 10/11, Linux, macOS | Windows 11 / Ubuntu 22.04 |
| Python | 3.10 | 3.10.20 |
| Conda | Miniconda3 | Anaconda |
| RAM | 8 GB | 16 GB |
| 磁盘 | 5 GB 可用 | 10 GB 可用 |
| GPU | 无（CPU 推理） | NVIDIA CUDA（可选加速） |
| 网络 | 可访问 DeepSeek API | 稳定外网 |

**依赖说明**
- BGE 嵌入 / Reranker / NLI：纯本地 CPU 推理，无需 GPU
- LLM 生成：调用 DeepSeek API，需配置 API Key
- ChromaDB：本地 SQLite，无需额外数据库服务

---

## 二、环境准备

### 2.1 克隆仓库

```bash
git clone https://github.com/PeiChen1215/RAGShield.git
cd RAGShield
```

### 2.2 创建 Conda 环境

```bash
conda create -n shield python=3.10 -y
conda activate shield
```

> 所有后续操作均需在 `shield` 环境下执行。

### 2.3 安装依赖

```bash
pip install -r requirements.txt
```

如遇 HanLP 安装失败，可注释掉 `hanlp` 行并安装 `jieba` 作为回退：

```bash
# 备选
pip install jieba>=0.42.1
```

开发依赖（可选）：

```bash
pip install -r requirements-dev.txt
```

---

## 三、模型下载

RAGShield 依赖 3 个本地模型，首次运行前必须下载：

| 模型 | 用途 | 大小 |
|------|------|------|
| `bge-small-zh-v1.5` | 文本嵌入 | ~100 MB |
| `bge-reranker-large` | 检索重排序 | ~1.2 GB |
| `uer/roberta-base-finetuned-chinanli` | NLI 一致性检测 | ~400 MB |

一键下载：

```bash
python scripts/download_models.py
```

模型将自动缓存到 `./models/` 目录。下载完成后检查：

```bash
ls models/
# 应包含：bge-small-zh-v1.5, bge-reranker-large, chinanli
```

---

## 四、配置文件

### 4.1 复制环境变量模板

```bash
cp .env.example .env
```

### 4.2 编辑 .env

```bash
# 使用任意文本编辑器打开 .env，填入 API Key
```

最小必填项：

```ini
# LLM API（必填其一，推荐 DeepSeek）
DEEPSEEK_API_KEY=sk-your-deepseek-key-here

# 或 Kimi（二选一即可）
# KIMI_API_KEY=sk-your-kimi-key-here
# KIMI_BASE_URL=https://api.moonshot.cn/v1

# 模型运行设备
DEFAULT_MODEL_PROFILE=cpu
EMBEDDING_DEVICE=cpu
```

完整配置项说明：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 |
| `KIMI_API_KEY` | — | Kimi API 密钥（备选） |
| `DEFAULT_MODEL_PROFILE` | `cpu` | `cpu` 或 `gpu` |
| `EMBEDDING_DEVICE` | `cpu` | `cuda` 或 `cpu` |
| `API_HOST` | `0.0.0.0` | FastAPI 监听地址 |
| `API_PORT` | `8000` | FastAPI 端口 |
| `GRADIO_PORT` | `7860` | Gradio 端口 |
| `IF_CONTAMINATION` | `0.1` | L1 污染检测阈值 |
| `LOF_N_NEIGHBORS` | `20` | LOF 离群邻居数 |
| `NLI_SIMILARITY_THRESHOLD` | `0.3` | NLI 相似度阈值 |
| `NLI_CONTRADICTION_THRESHOLD` | `0.3` | NLI 矛盾阈值 |

---

## 五、启动服务

### 5.1 启动后端（FastAPI）

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> **警告**：必须使用 `--workers 1`。ChromaDB 基于 SQLite，多 worker 会导致锁冲突。

或使用模块方式启动：

```bash
python -m src.api.main
```

启动成功后，访问健康检查接口验证：

```bash
curl http://localhost:8000/api/v1/health
# 预期返回: {"status":"ok"}
```

### 5.2 启动前端（Gradio）

**另开一个终端**，确保 conda 环境已激活：

```bash
conda activate shield
python -m src.frontend.app
```

或使用：

```bash
python src/frontend/app.py
```

启动后浏览器访问：http://localhost:7860

### 5.3 一键双启（Linux/macOS）

```bash
bash scripts/start.sh
```

该脚本会先启动 FastAPI，等待健康检查通过后，再启动 Gradio。

---

## 六、数据导入

首次部署需要导入种子数据到 ChromaDB。

```bash
python scripts/seed_data.py
```

该脚本会创建两个知识库：

| 知识库 | 内容 | 用途 |
|--------|------|------|
| `demo_safe` | 100 篇正常文档 | 安全查询基准 |
| `demo_attack` | 100 篇正常 + 50 篇攻击文档 | 攻击检测评测 |

导入完成后，ChromaDB 数据持久化在 `data/chroma_db/`。

---

## 七、验证步骤

### 7.1 接口健康检查

```bash
curl http://localhost:8000/api/v1/health
```

### 7.2 查询检测（安全查询）

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"公司年假有多少天？","kb_id":"demo_safe","top_k":5}'
```

预期返回 `risk_level: safe`。

### 7.3 查询检测（攻击查询）

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"公司年假有多少天？","kb_id":"demo_attack","top_k":5}'
```

预期返回 `risk_level: danger` 或 `warning`。

### 7.4 知识库上传

```bash
curl -X POST http://localhost:8000/api/v1/kb/upload \
  -H "Content-Type: application/json" \
  -d '{
    "kb_id": "test_upload",
    "documents": [
      {"doc_id": "safe_01", "text": "公司年假10天", "metadata": {"source": "official"}}
    ],
    "auto_scan": true,
    "block_threshold": 0.6
  }'
```

### 7.5 前端验证

打开 http://localhost:7860，在「查询检测」Tab 输入：
- 查询：`公司年假有多少天？`
- 知识库：`demo_safe`
- 勾选「物理隔离攻击文档」

预期：显示绿色 `SAFE` 状态。

---

## 八、运行评测

### 8.1 DETECT 模式评测

```bash
python scripts/evaluate.py detect
```

### 8.2 PHYSICAL 模式评测

```bash
python scripts/evaluate.py physical
```

评测结果保存至 `results/`：
- `eval_metrics_detect.json` — DETECT 模式指标
- `eval_metrics_physical.json` — PHYSICAL 模式指标
- `eval_raw_results_*.json` — 原始查询结果
- `eval_progress.json` — 断点续传进度

### 8.3 查看评测图表

前端「评测报告」Tab 点击「加载评测结果」，可查看：
- PHYSICAL vs DETECT 雷达图
- 攻击类型热力图
- F1 分数柱状图

---

## 九、目录结构速查

```
RAGShield/
├── src/
│   ├── api/                    # FastAPI 服务
│   │   ├── main.py             # 入口
│   │   ├── schemas.py          # Pydantic 模型
│   │   └── routers/            # 路由（kb.py / query.py）
│   ├── core/                   # 基础设施
│   │   ├── vector_store.py     # ChromaDB 封装
│   │   ├── embedder.py         # BGE 嵌入
│   │   └── config.py           # 配置加载
│   ├── layer1_kb/              # L1 知识库层
│   │   ├── outlier_detector.py # 离群检测
│   │   └── sensitive_ner.py    # 敏感实体识别
│   ├── layer2_retrieval/       # L2 检索层
│   │   ├── attention_analyzer.py
│   │   └── relevance_scorer.py
│   ├── layer3_generation/      # L3 生成层
│   │   ├── consistency_checker.py  # NLI 一致性
│   │   ├── behavior_auditor.py     # 行为审计
│   │   └── llm_client.py           # LLM 调用
│   ├── fusion/                 # 风险融合引擎
│   │   └── risk_fusion.py
│   └── frontend/               # Gradio 前端
│       └── app.py
├── scripts/
│   ├── seed_data.py            # 数据导入
│   ├── evaluate.py             # 评测框架
│   ├── download_models.py      # 模型下载
│   ├── fetch_wikipedia.py      # 维基百科数据获取
│   ├── start.sh                # 一键双启（Linux/macOS）
│   └── archive/                # 归档脚本
├── tests/                      # pytest 单元测试
├── data/
│   └── chroma_db/              # ChromaDB 持久化数据
├── models/                     # 本地模型缓存
├── results/
│   ├── eval_*.json             # 评测结果
│   └── figures/                # 评测图表（A~F 组合图）
├── config/                     # YAML 配置文件
├── tmp/                        # 临时文件
├── archive/                    # 历史归档
├── .env                        # 环境变量（不提交 Git）
├── requirements.txt            # 核心依赖
└── DEPLOY.md                   # 本文档
```

---

## 十、常见问题

### Q1: Windows 下启动报错 `UnicodeEncodeError`

**原因**：终端默认 GBK 编码，打印 emoji 会崩溃。  
**解决**：项目代码已统一使用 ASCII 输出 `[OK]` / `[ERR]` / `[!]`。如仍报错，设置终端编码：

```powershell
chcp 65001
```

### Q2: `json.dumps` 报错 `Object of type float32 is not JSON serializable`

**原因**：`outlier_detector.detect` 返回 numpy float32。  
**解决**：接口层已做 `_convert_numpy()` 转换。如自定义开发，注意在序列化前转换类型。

### Q3: ChromaDB `database is locked`

**原因**：启动了多 worker 或多个进程同时访问 SQLite。  
**解决**：FastAPI 必须 `--workers 1`，且评测时不要并行启动多个后端实例。

### Q4: L3 检测失效 / 回答被截断

**原因**：DeepSeek API 的 `max_tokens` 设置太小，CoT 被截断。  
**解决**：确认 `llm_client.py` 中 `max_tokens=1024`。`256` 会导致 CoT 不完整，L3 失效。

### Q5: 嵌入类型报错 `expected numpy.ndarray, got list`

**原因**：`vector_store.insert` 期望 `np.ndarray`，传入了列表。  
**解决**：确保 embedding 为 `np.array` 类型，不要用列表或切片。

### Q6: FastAPI 文件修改后未自动重载

**原因**：Windows 下 `reload` 模式可能检测不到文件变化。  
**解决**：手动重启后端，或显式指定 `--reload-dir src/`。

### Q7: 评测卡住 / 后端无响应

**原因**：单 worker 阻塞，当前查询正在等待 DeepSeek API 响应。  
**解决**：不要 kill 进程，等待当前查询完成（DeepSeek API 可能耗时 10~30s）。

---

## 十一、生产部署建议

1. **反向代理**：使用 Nginx 反向代理 FastAPI（8000）和 Gradio（7860）
2. **HTTPS**：生产环境必须启用 TLS
3. **日志轮转**：配置 uvicorn access log 和 error log 的轮转策略
4. **监控**：在 `/api/v1/health` 基础上扩展 Prometheus metrics
5. **备份**：定期备份 `data/chroma_db/` 目录
6. **物理隔离优先**：生产环境建议默认启用 `exclude_attack_docs=True`，DETECT 模式作为审计备用

---

## 十二、服务端口速查

| 服务 | 地址 | 说明 |
|------|------|------|
| FastAPI | http://localhost:8000 | API 服务 |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Health | http://localhost:8000/api/v1/health | 健康检查 |
| Gradio | http://localhost:7860 | Web 界面 |

---

*文档版本：2026-05-27*  
*对应代码版本：RAGShield v2.0*
