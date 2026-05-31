"""
v2/api/schemas.py
RAGShield V2 FastAPI 请求/响应模型
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class Document(BaseModel):
    doc_id: str = Field(..., description="文档唯一标识")
    text: str = Field(..., description="文档正文", min_length=1)
    metadata: Dict = Field(default={}, description="文档元数据")


class RetrievedDocument(Document):
    relevance_score: float = Field(..., ge=0, le=1, description="与查询的相似度分数")


# ---------- 请求模型 ----------


class KBUploadRequest(BaseModel):
    documents: List[Document] = Field(..., min_length=1, max_length=100)
    auto_scan: bool = Field(default=True, description="是否自动触发 Layer1 扫描")
    kb_id: Optional[str] = Field(default=None, description="知识库 ID")
    block_threshold: float = Field(default=1.0, ge=0.0, le=1.0)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="用户查询文本")
    kb_id: str = Field(default="default", description="知识库 ID")
    generate_answer: bool = Field(default=True, description="是否调用 LLM 生成回答")
    skip_layer0: bool = Field(default=False, description="调试时跳过 Layer0")


# ---------- 响应模型 ----------


class DetectorResult(BaseModel):
    detector_name: str = ""
    score: float = 0.0
    risk_level: str = "safe"
    reason: str = ""
    details: Dict = {}


class Layer0Result(BaseModel):
    blocked: bool = False
    risk_score: float = 0.0
    risk_level: str = "safe"
    triggered_rules: List[str] = []
    reason: str = ""


class Layer1Result(BaseModel):
    action: str = "pass"
    risk_score: float = 0.0
    risk_level: str = "safe"
    triggered_dimensions: List[str] = []
    reason: str = ""
    detector_results: Dict[str, DetectorResult] = {}


class FactItem(BaseModel):
    type: str = "other"
    content: str = ""
    source_doc_id: str = ""
    confidence: float = 0.0
    risk_level: str = "safe"
    risk_reason: Optional[str] = None


class ConflictItem(BaseModel):
    conflict_type: str = ""
    topic: str = ""
    description: str = ""
    severity: float = 0.0


class Layer4Result(BaseModel):
    verified_facts_count: int = 0
    unverified_facts_count: int = 0
    conflicts: List[ConflictItem] = []
    overall_risk: float = 0.0
    reason: str = ""


class FusionResult(BaseModel):
    final_score: float = 0.0
    triggered_layers: List[str] = []
    reason: str = ""


class QueryResponse(BaseModel):
    query: str = ""
    action: str = "pass"  # pass | review | block
    risk_level: str = "safe"
    final_risk_score: float = 0.0
    answer: Optional[str] = None
    warning_message: Optional[str] = None
    
    layer0: Optional[Layer0Result] = None
    layer2_risky_doc_count: int = 0
    layer3_facts: List[FactItem] = []
    layer4: Optional[Layer4Result] = None
    layer6_is_safe: bool = True
    layer6_risk_score: float = 0.0
    
    fusion: Optional[FusionResult] = None
    latency_ms: float = 0.0
    trace_id: str = ""


class KBUploadResult(BaseModel):
    doc_id: str = ""
    action: str = "pass"
    risk_score: float = 0.0
    reason: str = ""


class KBUploadResponse(BaseModel):
    kb_id: str = ""
    total: int = 0
    passed: int = 0
    blocked: int = 0
    review: int = 0
    results: List[KBUploadResult] = []
    latency_ms: float = 0.0
