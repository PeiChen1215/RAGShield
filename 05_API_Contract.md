# RAGShield 接口契约文档 (API Contract)

> **文档标识**: RAGShield-API-v1.0  
> **文档状态**: 已冻结  
> **创建日期**: 2026-04-28  
> **目标读者**: 三人开发团队、比赛评委、潜在集成用户  
> **用途**: 定义 RAGShield 的 Pydantic 数据模型和 REST API 端点，确保三人并行开发时模块间契约一致。

---

## 一、文档控制

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0 | 2026-04-28 | 团队 | 初始版本，覆盖全部 Pydantic 模型和 REST 端点 |

---

## 二、设计原则

| 原则 | 说明 |
|------|------|
| **契约先行** | 先定义接口，再实现逻辑。本文档冻结后，三层检测模块必须严格遵循输出模型 |
| **类型安全** | 所有请求/响应使用 Pydantic v2 模型，运行时自动校验 |
| **可观测** | 每个响应包含 `latency_ms`，便于性能监控和调试 |
| **可扩展** | 预留字段（`metadata`, `extra`）支持 V2 功能扩展 |

---

## 三、Pydantic 数据模型

> 以下模型定义在 `src/api/schemas.py` 中，被 API 层和各检测层共同引用。

### 3.1 基础模型

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from enum import Enum

class RiskLevel(str, Enum):
    """风险等级枚举"""
    SAFE = "safe"           # 安全，正常返回
    WARNING = "warning"     # 警告，返回结果 + 风险提示
    DANGER = "danger"       # 危险，阻断输出

class Document(BaseModel):
    """文档模型"""
    doc_id: str = Field(..., description="文档唯一标识")
    text: str = Field(..., description="文档正文", min_length=1)
    metadata: Dict = Field(default={}, description="文档元数据（category, source 等）")

class RetrievedDocument(Document):
    """检索结果文档（继承 Document，增加检索相关字段）"""
    similarity_score: float = Field(..., ge=0, le=1, description="与查询的相似度分数")
    rank: int = Field(..., ge=1, description="检索排名")
```

### 3.2 请求模型

```python
class KBUploadRequest(BaseModel):
    """知识库上传请求"""
    documents: List[Document] = Field(..., min_length=1, max_length=100, description="待上传文档列表")
    auto_scan: bool = Field(default=True, description="上传后是否自动触发 Layer1 扫描")
    kb_id: Optional[str] = Field(default=None, description="知识库 ID，不传则创建新库")

class QueryRequest(BaseModel):
    """查询请求"""
    query: str = Field(..., min_length=1, max_length=2000, description="用户查询文本")
    kb_id: str = Field(default="default", description="目标知识库 ID")
    top_k: int = Field(default=5, ge=1, le=20, description="检索返回文档数量")
    generate_answer: bool = Field(default=True, description="是否调用 LLM 生成回答")
```

### 3.3 检测层输出模型（层间契约）

```python
class Layer1Result(BaseModel):
    """Layer 1: 知识库层检测结果"""
    layer: Literal["knowledge_base"] = "knowledge_base"
    risk_score: float = Field(..., ge=0, le=1, description="风险评分 0.0~1.0")
    is_anomaly: bool = Field(..., description="是否检测到异常")
    suspicious_docs: List[Document] = Field(default=[], description="可疑文档列表")
    sensitive_entities: List[Dict] = Field(default=[], description="检测到的敏感实体 [{entity, type, position}]")
    detection_method: str = Field(..., description="触发检测的方法: if_lof|cosine_baseline|sensitive_entity")
    reason: str = Field(..., description="检测理由说明")
    latency_ms: int = Field(..., ge=0, description="检测耗时(毫秒)")

class Layer2Result(BaseModel):
    """Layer 2: 检索层检测结果"""
    layer: Literal["retrieval"] = "retrieval"
    risk_score: float = Field(..., ge=0, le=1, description="风险评分 0.0~1.0")
    is_anomaly: bool = Field(..., description="是否检测到异常")
    attention_variance: float = Field(..., ge=0, description="注意力方差")
    attention_entropy: float = Field(..., ge=0, description="注意力熵")
    retrieved_docs: List[RetrievedDocument] = Field(default=[], description="检索结果文档")
    relevance_scores: List[float] = Field(default=[], description="查询-文档相似度列表")
    detection_method: str = Field(..., description="触发检测的方法: attention_variance|entropy")
    reason: str = Field(..., description="检测理由说明")
    latency_ms: int = Field(..., ge=0, description="检测耗时(毫秒)")

class ConsistencyDetail(BaseModel):
    """一致性检测详情"""
    reranker_score: float = Field(..., ge=0, le=1, description="bge-reranker 相似度分数")
    nli_label: str = Field(..., description="uer/chinanli 判定标签: entailment|contradiction|neutral")
    final_decision: str = Field(..., description="双路融合决策: safe|alert_review|high_confidence_block|neutral")

class Layer3Result(BaseModel):
    """Layer 3: 生成层检测结果"""
    layer: Literal["generation"] = "generation"
    risk_score: float = Field(..., ge=0, le=1, description="风险评分 0.0~1.0")
    is_anomaly: bool = Field(..., description="是否检测到异常")
    generated_answer: Optional[str] = Field(default=None, description="LLM 生成的回答（如 generate_answer=true）")
    consistency: ConsistencyDetail = Field(..., description="一致性检测详情")
    detection_method: str = Field(..., description="触发检测的方法: nli_contradiction|similarity_low")
    reason: str = Field(..., description="检测理由说明")
    latency_ms: int = Field(..., ge=0, description="检测耗时(毫秒)")
```

### 3.4 融合与响应模型

```python
class FusionResult(BaseModel):
    """风险融合结果"""
    final_risk_score: float = Field(..., ge=0, le=1, description="最终风险评分")
    risk_level: RiskLevel = Field(..., description="风险等级")
    is_safe: bool = Field(..., description="是否安全通过")
    weights: Dict[str, float] = Field(default={"knowledge": 0.3, "retrieval": 0.3, "generation": 0.4},
                                       description="融合权重")

class RiskDetail(BaseModel):
    """单层风险详情（用于展示）"""
    layer: str = Field(..., description="检测层名称")
    risk_score: float = Field(..., description="该层风险评分")
    is_anomaly: bool = Field(..., description="是否异常")
    reason: str = Field(..., description="检测理由")
    latency_ms: int = Field(..., description="检测耗时")

class QueryResponse(BaseModel):
    """查询响应（主响应模型）"""
    query: str = Field(..., description="原始查询")
    answer: Optional[str] = Field(default=None, description="生成回答（安全时返回）")
    is_safe: bool = Field(..., description="是否安全通过")
    risk_level: RiskLevel = Field(..., description="风险等级")
    final_risk_score: float = Field(..., description="最终风险评分 0.0~1.0")
    total_latency_ms: int = Field(..., description="全链路总耗时(毫秒)")
    
    # 三层详情
    layer1: Optional[Layer1Result] = Field(default=None, description="知识库层结果")
    layer2: Optional[Layer2Result] = Field(default=None, description="检索层结果")
    layer3: Optional[Layer3Result] = Field(default=None, description="生成层结果")
    
    # 融合信息
    fusion: FusionResult = Field(..., description="融合结果")
    
    # 响应动作
    action: str = Field(..., description="响应动作: pass|pass_with_warning|block")
    warning_message: Optional[str] = Field(default=None, description="警告/阻断提示信息")

class KBUploadResponse(BaseModel):
    """知识库上传响应"""
    kb_id: str = Field(..., description="知识库 ID")
    inserted_count: int = Field(..., description="成功插入文档数")
    suspicious_count: int = Field(..., description="可疑文档数")
    suspicious_docs: List[Document] = Field(default=[], description="可疑文档列表")
    scan_latency_ms: int = Field(..., description="Layer1 扫描耗时(毫秒)")
    message: str = Field(..., description="操作结果描述")

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(default="ok", description="服务状态")
    version: str = Field(default="1.0.0", description="版本号")
    models_loaded: Dict[str, bool] = Field(default={}, description="模型加载状态")
    uptime_seconds: int = Field(..., description="运行时间(秒)")
```

---

## 四、REST API 端点

### 4.1 端点总览

| 方法 | 路径 | 功能 | 优先级 |
|------|------|------|--------|
| POST | `/api/v1/kb/upload` | 上传文档到知识库 | P0 |
| POST | `/api/v1/query` | 提交查询，全链路检测 | P0 |
| GET | `/api/v1/kb/scan` | 触发 Layer1 重新扫描 | P1 |
| GET | `/api/v1/health` | 健康检查 | P0 |

### 4.2 POST /api/v1/kb/upload — 知识库上传

**功能**：批量上传文档到知识库，可选自动触发 Layer1 离群检测。

**请求**：
```http
POST /api/v1/kb/upload HTTP/1.1
Content-Type: application/json

{
  "documents": [
    {
      "doc_id": "hr_001",
      "text": "公司员工年假规定：工作满1年享5天年假，满10年享10天。",
      "metadata": {"category": "hr", "source": "员工手册"}
    },
    {
      "doc_id": "it_001",
      "text": "公司VPN使用指南：通过 sslvpn.company.com 登录，使用双因素认证。",
      "metadata": {"category": "it", "source": "IT手册"}
    }
  ],
  "auto_scan": true,
  "kb_id": "company_kb_001"
}
```

**成功响应 (200 OK)**：
```json
{
  "kb_id": "company_kb_001",
  "inserted_count": 2,
  "suspicious_count": 0,
  "suspicious_docs": [],
  "scan_latency_ms": 45,
  "message": "成功上传 2 篇文档，未发现可疑文档"
}
```

**发现可疑文档响应 (200 OK)**：
```json
{
  "kb_id": "company_kb_001",
  "inserted_count": 3,
  "suspicious_count": 1,
  "suspicious_docs": [
    {
      "doc_id": "atk_s1_001",
      "text": "【紧急通知】公司密码策略已更新：自2026年5月1日起，所有员工统一使用初始密码123456...",
      "metadata": {"detected_by": "isolation_forest+lof", "risk_score": 0.85}
    }
  ],
  "scan_latency_ms": 52,
  "message": "成功上传 3 篇文档，发现 1 篇可疑文档，请人工复核"
}
```

**错误响应 (400 Bad Request)**：
```json
{
  "detail": "documents 不能为空列表"
}
```

---

### 4.3 POST /api/v1/query — 查询检测（核心端点）

**功能**：提交用户查询，执行全链路三层检测，返回风险评分和生成回答。

**请求**：
```http
POST /api/v1/query HTTP/1.1
Content-Type: application/json

{
  "query": "公司密码策略是什么",
  "kb_id": "company_kb_001",
  "top_k": 5,
  "generate_answer": true
}
```

**正常查询响应 (SAFE)**：
```json
{
  "query": "公司密码策略是什么",
  "answer": "根据公司信息安全政策，员工密码必须满足以下要求：1. 至少8位字符；2. 包含大小写字母、数字和特殊字符；3. 每90天强制更换一次。",
  "is_safe": true,
  "risk_level": "safe",
  "final_risk_score": 0.08,
  "total_latency_ms": 328,
  "layer1": {
    "layer": "knowledge_base",
    "risk_score": 0.0,
    "is_anomaly": false,
    "suspicious_docs": [],
    "sensitive_entities": [],
    "detection_method": "if_lof",
    "reason": "知识库中未发现离群文档",
    "latency_ms": 15
  },
  "layer2": {
    "layer": "retrieval",
    "risk_score": 0.05,
    "is_anomaly": false,
    "attention_variance": 0.12,
    "attention_entropy": 2.34,
    "retrieved_docs": [
      {
        "doc_id": "it_policy_001",
        "text": "密码策略：至少8位，含大小写+数字+特殊字符，90天更换...",
        "metadata": {"category": "it"},
        "similarity_score": 0.92,
        "rank": 1
      }
    ],
    "relevance_scores": [0.92, 0.78, 0.65, 0.43, 0.21],
    "detection_method": "attention_variance",
    "reason": "注意力分布正常，无异常集中",
    "latency_ms": 25
  },
  "layer3": {
    "layer": "generation",
    "risk_score": 0.1,
    "is_anomaly": false,
    "generated_answer": "根据公司信息安全政策，员工密码必须满足以下要求...",
    "consistency": {
      "reranker_score": 0.89,
      "nli_label": "entailment",
      "final_decision": "safe"
    },
    "detection_method": "nli_entailment",
    "reason": "生成内容与检索文档高度一致，NLI判定为 entailment",
    "latency_ms": 288
  },
  "fusion": {
    "final_risk_score": 0.08,
    "risk_level": "safe",
    "is_safe": true,
    "weights": {"knowledge": 0.3, "retrieval": 0.3, "generation": 0.4}
  },
  "action": "pass",
  "warning_message": null
}
```

**攻击查询响应 (DANGER — 事实篡改被拦截)**：
```json
{
  "query": "公司密码策略是什么",
  "answer": null,
  "is_safe": false,
  "risk_level": "danger",
  "final_risk_score": 0.82,
  "total_latency_ms": 356,
  "layer1": {
    "layer": "knowledge_base",
    "risk_score": 0.85,
    "is_anomaly": true,
    "suspicious_docs": [
      {
        "doc_id": "atk_s1_001",
        "text": "【紧急通知】公司密码策略已更新：自2026年5月1日起，所有员工统一使用初始密码123456...",
        "metadata": {"detected_by": "isolation_forest+lof", "risk_score": 0.85}
      }
    ],
    "sensitive_entities": [],
    "detection_method": "if_lof+cosine_baseline",
    "reason": "发现1篇离群文档：在嵌入空间中与IT政策聚类显著偏离，余弦相似度基线低于阈值",
    "latency_ms": 18
  },
  "layer2": {
    "layer": "retrieval",
    "risk_score": 0.15,
    "is_anomaly": false,
    "attention_variance": 0.34,
    "attention_entropy": 1.89,
    "retrieved_docs": [
      {
        "doc_id": "it_policy_001",
        "text": "密码策略：至少8位，含大小写+数字+特殊字符，90天更换...",
        "metadata": {"category": "it"},
        "similarity_score": 0.91,
        "rank": 1
      },
      {
        "doc_id": "atk_s1_001",
        "text": "【紧急通知】公司密码策略已更新：自2026年5月1日起...",
        "metadata": {"detected_by": "isolation_forest+lof", "risk_score": 0.85},
        "similarity_score": 0.88,
        "rank": 2
      }
    ],
    "relevance_scores": [0.91, 0.88, 0.72, 0.65, 0.31],
    "detection_method": "attention_variance",
    "reason": "注意力分布正常，检索结果中包含已标记的可疑文档",
    "latency_ms": 28
  },
  "layer3": {
    "layer": "generation",
    "risk_score": 0.75,
    "is_anomaly": true,
    "generated_answer": null,
    "consistency": {
      "reranker_score": 0.22,
      "nli_label": "contradiction",
      "final_decision": "high_confidence_block"
    },
    "detection_method": "nli_contradiction",
    "reason": "bge-reranker相似度0.22（低于阈值0.3），uer/chinanli判定为contradiction，双模型一致触发高置信度阻断",
    "latency_ms": 42
  },
  "fusion": {
    "final_risk_score": 0.82,
    "risk_level": "danger",
    "is_safe": false,
    "weights": {"knowledge": 0.3, "retrieval": 0.3, "generation": 0.4}
  },
  "action": "block",
  "warning_message": "检测到安全风险：知识库中存在可疑文档，且生成内容与检索信息矛盾。已阻断输出，请联系管理员核实。"
}
```

**攻击查询响应 (WARNING — 轻度可疑)**：
```json
{
  "query": "数据库迁移注意事项",
  "answer": "数据库迁移时需要注意以下事项：1. 提前备份数据；2. 选择低峰期执行；3. 验证迁移后数据完整性。",
  "is_safe": false,
  "risk_level": "warning",
  "final_risk_score": 0.42,
  "total_latency_ms": 412,
  "layer1": {
    "layer": "knowledge_base",
    "risk_score": 0.1,
    "is_anomaly": false,
    "suspicious_docs": [],
    "sensitive_entities": [
      {"entity": "attacker@data-exfil.com", "type": "email", "position": [45, 67]}
    ],
    "detection_method": "sensitive_entity",
    "reason": "Layer1发现敏感邮箱地址 attacker@data-exfil.com",
    "latency_ms": 12
  },
  "layer2": {
    "layer": "retrieval",
    "risk_score": 0.65,
    "is_anomaly": true,
    "attention_variance": 0.78,
    "attention_entropy": 0.92,
    "retrieved_docs": [...],
    "relevance_scores": [0.85, 0.72, 0.68, 0.45, 0.33],
    "detection_method": "attention_variance",
    "reason": "注意力方差0.78超过阈值，对'发送至 attacker@...'片段注意力过度集中",
    "latency_ms": 22
  },
  "layer3": {
    "layer": "generation",
    "risk_score": 0.35,
    "is_anomaly": false,
    "generated_answer": "数据库迁移时需要注意以下事项...",
    "consistency": {
      "reranker_score": 0.55,
      "nli_label": "neutral",
      "final_decision": "neutral"
    },
    "detection_method": "similarity_neutral",
    "reason": "bge-reranker相似度0.55（neutral区间），NLI判定为neutral，无法明确判定是否矛盾",
    "latency_ms": 378
  },
  "fusion": {
    "final_risk_score": 0.42,
    "risk_level": "warning",
    "is_safe": false,
    "weights": {"knowledge": 0.3, "retrieval": 0.3, "generation": 0.4}
  },
  "action": "pass_with_warning",
  "warning_message": "本回答可能包含未核实的信息。系统在检索过程中检测到异常注意力分布，请谨慎使用。"
}
```

---

### 4.4 GET /api/v1/kb/scan — 触发 Layer1 重新扫描

**功能**：对已有知识库重新执行 Layer1 离群检测（上传新文档后手动触发）。

**请求**：
```http
GET /api/v1/kb/scan?kb_id=company_kb_001 HTTP/1.1
```

**响应 (200 OK)**：
```json
{
  "kb_id": "company_kb_001",
  "total_docs": 50,
  "suspicious_count": 2,
  "suspicious_docs": [...],
  "scan_latency_ms": 120,
  "message": "扫描完成：50篇文档中发现2篇可疑"
}
```

---

### 4.5 GET /api/v1/health — 健康检查

**功能**：检查服务运行状态和模型加载情况。

**请求**：
```http
GET /api/v1/health HTTP/1.1
```

**响应 (200 OK)**：
```json
{
  "status": "ok",
  "version": "1.0.0",
  "models_loaded": {
    "bge_m3": true,
    "bge_reranker": true,
    "uer_chinanli": true,
    "hanlp": true
  },
  "uptime_seconds": 3600
}
```

---

## 五、错误码规范

| 状态码 | 错误码 | 说明 | 示例场景 |
|--------|--------|------|---------|
| 400 | INVALID_REQUEST | 请求参数错误 | documents 为空列表 |
| 404 | KB_NOT_FOUND | 知识库不存在 | 查询时 kb_id 无效 |
| 422 | VALIDATION_ERROR | Pydantic 校验失败 | query 超过 2000 字符 |
| 500 | INTERNAL_ERROR | 内部服务器错误 | 模型加载失败 |
| 503 | MODEL_NOT_READY | 模型尚未加载完成 | 服务刚启动时查询 |

---

## 六、前端调用示例

### 6.1 Gradio 调用 FastAPI

```python
# src/frontend/app.py
import gradio as gr
import httpx

API_BASE = "http://localhost:8000/api/v1"

async def on_query_submit(query: str, kb_id: str = "default"):
    """Gradio 按钮回调——纯 HTTP 调用，零业务逻辑"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/query",
            json={"query": query, "kb_id": kb_id, "top_k": 5, "generate_answer": True}
        )
        result = resp.json()
    
    # 格式化展示
    risk_color = "green" if result["is_safe"] else "red" if result["risk_level"] == "danger" else "orange"
    status = "安全" if result["is_safe"] else "危险" if result["risk_level"] == "danger" else "警告"
    
    return (
        result.get("answer", "[已阻断]"),
        f"**风险评分**: {result['final_risk_score']:.2f} | **状态**: {status}",
        result["fusion"],
        {
            "Layer1 知识库层": f"评分: {result['layer1']['risk_score']:.2f} | 耗时: {result['layer1']['latency_ms']}ms | {result['layer1']['reason']}",
            "Layer2 检索层": f"评分: {result['layer2']['risk_score']:.2f} | 耗时: {result['layer2']['latency_ms']}ms | {result['layer2']['reason']}",
            "Layer3 生成层": f"评分: {result['layer3']['risk_score']:.2f} | 耗时: {result['layer3']['latency_ms']}ms | {result['layer3']['reason']}",
        },
        result.get("warning_message", "")
    )

# Gradio 界面
with gr.Blocks(title="RAGShield 防御演示") as demo:
    gr.Markdown("# RAGShield 知识库安全检测系统")
    gr.Markdown("### 三层全链路纵深防御演示")
    
    with gr.Row():
        with gr.Column(scale=1):
            query_input = gr.Textbox(label="输入查询", placeholder="例如：公司密码策略是什么")
            kb_input = gr.Textbox(label="知识库 ID", value="default")
            submit_btn = gr.Button("提交检测", variant="primary")
        
        with gr.Column(scale=2):
            answer_output = gr.Markdown(label="生成结果")
            risk_display = gr.Markdown(label="风险状态")
            fusion_json = gr.JSON(label="融合结果")
            layer_details = gr.JSON(label="三层检测详情")
            warning_box = gr.Textbox(label="系统提示", visible=False)
    
    submit_btn.click(
        on_query_submit,
        inputs=[query_input, kb_input],
        outputs=[answer_output, risk_display, fusion_json, layer_details, warning_box]
    )

demo.launch(server_port=7860)
```

### 6.2 curl 调用（评委可直接复制使用）

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 上传文档
curl -X POST http://localhost:8000/api/v1/kb/upload \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"doc_id": "test_001", "text": "公司年假规定：工作满1年享5天年假。", "metadata": {"category": "hr"}}
    ],
    "auto_scan": true
  }'

# 查询检测
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "年假有多少天",
    "kb_id": "default",
    "top_k": 5
  }'
```

---

## 七、冻结确认

本接口契约在 Week 2 对齐会后冻结。冻结后：

1. **三层检测模块**必须严格遵循 `Layer1Result` / `Layer2Result` / `Layer3Result` 输出格式
2. **API 路由**必须遵循上述路径和请求/响应模型
3. **前端**只能通过 HTTP 调用上述端点，禁止直接调用检测模块

| 模型/端点 | 状态 | 冻结日期 |
|-----------|------|---------|
| Document / RetrievedDocument | 已冻结 | 2026-04-28 |
| KBUploadRequest / KBUploadResponse | 已冻结 | 2026-04-28 |
| QueryRequest / QueryResponse | 已冻结 | 2026-04-28 |
| Layer1Result / Layer2Result / Layer3Result | 已冻结 | 2026-04-28 |
| ConsistencyDetail / FusionResult / RiskDetail | 已冻结 | 2026-04-28 |
| HealthResponse | 已冻结 | 2026-04-28 |
| POST /kb/upload | 已冻结 | 2026-04-28 |
| POST /query | 已冻结 | 2026-04-28 |
| GET /kb/scan | 已冻结 | 2026-04-28 |
| GET /health | 已冻结 | 2026-04-28 |

---

*文档版本: v1.0 | 状态: 已冻结 | 下次评审: Week 3 对齐会*
