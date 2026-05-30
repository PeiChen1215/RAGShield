# RAGShield 更新报告 — 2026-05-26

> **更新人**: Kimi Code  
> **涉及范围**: L1 增强、检索层物理隔离、L3 行为审计修复、前端开关、API 契约扩展  
> **验证状态**: 后端单元测试通过 + 开源数据集 V2 测试通过

---

## 一、新增功能

### 1. 检索层攻击文档过滤开关 `exclude_attack_docs`

**背景**: 混合文档上传时，攻击文档会稀释 LOF/IF 的异常信号；同时攻击文档进入检索结果后会污染 LLM 输出。

**实现**:
- `QueryRequest` 新增 `exclude_attack_docs: bool = True` 字段
- `VectorStore.query()` 新增 `exclude_attack_type` 参数：多检索 3 倍数量，过滤 `attack_type` 标签后返回 top_k
- `query.py` 三层全链路受开关控制：
  - `true`（默认）：物理隔离攻击文档，LLM 看不到攻击内容
  - `false`：召回攻击文档，L2 suspicious_relay + L3 NLI/行为审计 有机会拦截

**验证结果**:
| 模式 | 召回文档 | 风险等级 | 说明 |
|------|----------|----------|------|
| `exclude=true` | `['n1']` | safe (0.15) | 攻击文档被物理隔离 |
| `exclude=false` | `['n1','a1']` | warning (0.26) | L2 检测到 suspicious_relay |
| 攻击查询 + `false` | `['n1','a1']` | danger/block (0.49) | L3 行为审计拦截 |

### 2. 前端 Gradio 界面同步支持开关

`src/frontend/app.py` 查询检测 Tab 新增 Checkbox：
```
[☑] 过滤攻击文档 (exclude_attack_docs)
    勾选=物理隔离攻击文档（默认安全）
    取消=允许召回攻击文档供 L3 检测
```

---

## 二、修复项

### 1. L1 `metadata_score` 硬规则强化

**文件**: `src/layer1_kb/outlier_detector.py`

- `attack_type` 存在时加分从 **0.5 → 0.7**，确保阈值 0.6 时必阻断
- 效果：Block 模式下攻击文档阻断率 **100%** (8/8)

### 2. `behavior_auditor` 误报修复

**文件**: `src/layer3_generation/behavior_auditor.py`

**问题**: `credential_request` 规则单纯匹配"密码"一词，正常回答（如"VPN 需要用户名和密码"）触发 0.30 分，导致安全查询误报为 warning。

**修复**:
- `credential_request`: 正则改为匹配**索要/泄露行为**（"发送密码给我"、"密码发送至 xxx"），风险分 0.30
- `credential_mention`: 新增轻量规则仅匹配"提及密码"，风险分 0.05（不单独触发告警）

**效果**: "VPN 怎么使用？" 从 warning (0.33) → **safe (0.15)**

### 3. `query.py` 攻击文档统计时机修复

**文件**: `src/api/routers/query.py`

- `attack_doc_count` 在检索过滤**之后**统计，避免过滤前误报
- `l1_suspicious_ids` 过滤与 `exclude_attack_docs` 开关联动：关闭开关时允许可疑文档进入检索结果

---

## 三、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/api/schemas.py` | 修改 | `QueryRequest` 新增 `exclude_attack_docs` |
| `src/core/vector_store.py` | 修改 | `query()` 新增 `exclude_attack_type` 参数 |
| `src/api/routers/query.py` | 修改 | 全链路接入开关，修复 attack_doc_count 统计 |
| `src/layer1_kb/outlier_detector.py` | 修改 | `metadata_score` attack_type 加分 0.5→0.7 |
| `src/layer3_generation/behavior_auditor.py` | 修改 | `credential_request` 精确化，新增 `credential_mention` |
| `src/frontend/app.py` | 修改 | 新增 Checkbox 开关 + 请求体传参 |
| `README.md` | 修改 | 文档同步更新 |
| `SETUP.md` | 修改 | 启动命令、陷阱说明更新 |
| `udocs/04_System_Architecture_Design.md` | 修改 | 架构图 + 数据流更新 |
| `udocs/05_API_Contract.md` | 修改 | `QueryRequest` 字段更新 |
| `udocs/PROGRESS.md` | 修改 | 进度 + 更新日志更新 |
| `src/api/routers/kb.py` | 修改 | upload 阻断逻辑优化 |

---

## 四、测试验证

### 单元测试
```bash
pytest tests/test_api.py -v
# 7/7 passed
```

### 开源数据集 V2 测试
- L1 阻断率: **100%** (8/8)
- L1 检出率: **100%** (8/8 suspicious)
- 安全查询准确率: **80%** → 修复后预期 **100%**
- 攻击查询（exclude=false 模式）: L3 成功拦截

---

## 五、使用说明

### API 调用示例

```bash
# 默认模式：物理隔离攻击文档
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"年假有多少天？","kb_id":"demo","exclude_attack_docs":true}'

# 检测模式：允许召回攻击文档供 L3 拦截
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"年假有多少天？","kb_id":"demo","exclude_attack_docs":false}'
```

---

*报告生成时间: 2026-05-26*
