"""
模块名: src/api/schemas.py
职责: 定义 RAGShield 的 Pydantic 请求/响应模型，作为三层检测模块间的契约。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """风险等级枚举。"""

    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"


class Document(BaseModel):
    """文档模型。"""

    doc_id: str = Field(..., description="文档唯一标识")
    text: str = Field(..., description="文档正文", min_length=1)
    metadata: Dict = Field(default={}, description="文档元数据（category, source 等）")


class RetrievedDocument(Document):
    """检索结果文档（继承 Document，增加检索相关字段）。"""

    similarity_score: float = Field(..., ge=0, le=1, description="与查询的相似度分数")
    rank: int = Field(..., ge=1, description="检索排名")


# ---------- 请求模型 ----------


class KBUploadRequest(BaseModel):
    """知识库上传请求。"""

    documents: List[Document] = Field(..., min_length=1, max_length=100, description="待上传文档列表")
    auto_scan: bool = Field(default=True, description="上传后是否自动触发 Layer1 扫描")
    kb_id: Optional[str] = Field(default=None, description="知识库 ID，不传则创建新库")


class QueryRequest(BaseModel):
    """查询请求。"""

    query: str = Field(..., min_length=1, max_length=2000, description="用户查询文本")
    kb_id: str = Field(default="default", description="目标知识库 ID")
    top_k: int = Field(default=5, ge=1, le=20, description="检索返回文档数量")
    generate_answer: bool = Field(default=True, description="是否调用 LLM 生成回答")


# ---------- 检测层输出模型 ----------


class Layer1Result(BaseModel):
    """Layer 1: 知识库层检测结果。"""

    layer: str = Field(default="knowledge_base", description="检测层名称")
    risk_score: float = Field(..., ge=0, le=1, description="风险评分 0.0~1.0")
    is_anomaly: bool = Field(..., description="是否检测到异常")
    suspicious_docs: List[Document] = Field(default=[], description="可疑文档列表")
    sensitive_entities: List[Dict] = Field(default=[], description="检测到的敏感实体 [{entity, type, position}]")
    detection_method: str = Field(..., description="触发检测的方法: if_lof|cosine_baseline|sensitive_entity")
    reason: str = Field(..., description="检测理由说明")
    latency_ms: int = Field(..., ge=0, description="检测耗时(毫秒)")


class Layer2Result(BaseModel):
    """Layer 2: 检索层检测结果。"""

    layer: str = Field(default="retrieval", description="检测层名称")
    risk_score: float = Field(..., ge=0, le=1, description="风险评分 0.0~1.0")
    is_anomaly: bool = Field(..., description="是否检测到异常")
    attention_variance: float = Field(..., ge=0, description="注意力方差（检索结果相似度分布的离散程度）")
    attention_entropy: float = Field(..., ge=0, description="注意力熵（检索结果相似度分布的信息熵）")
    retrieved_docs: List[RetrievedDocument] = Field(default=[], description="检索结果文档")
    relevance_scores: List[float] = Field(default=[], description="查询-文档相似度列表")
    suspicious_doc_count: int = Field(default=0, ge=0, description="检索结果中包含的已标记可疑文档数量（Layer1 接力协同）")
    detection_method: str = Field(..., description="触发检测的方法: attention_variance|attention_variance+suspicious_relay|entropy")
    reason: str = Field(..., description="检测理由说明")
    latency_ms: int = Field(..., ge=0, description="检测耗时(毫秒)")


class ConsistencyDetail(BaseModel):
    """一致性检测详情。"""

    reranker_score: float = Field(..., ge=0, le=1, description="bge-reranker 相似度分数")
    nli_label: str = Field(..., description="uer/chinanli 判定标签: entailment|contradiction|neutral|skipped")
    final_decision: str = Field(..., description="双路融合决策: safe|alert_review|high_confidence_block|neutral|skipped")


class Layer3Result(BaseModel):
    """Layer 3: 生成层检测结果。"""

    layer: str = Field(default="generation", description="检测层名称")
    risk_score: float = Field(..., ge=0, le=1, description="风险评分 0.0~1.0")
    is_anomaly: bool = Field(..., description="是否检测到异常")
    generated_answer: Optional[str] = Field(
        default=None,
        description="LLM 生成的原始回答内容。SAFE/WARNING 时为正常答案；DANGER 时为被阻断的原始生成内容。generate_answer=false 时为 null",
    )
    consistency: ConsistencyDetail = Field(..., description="一致性检测详情")
    detection_method: str = Field(..., description="触发检测的方法: nli_contradiction|similarity_low|skipped")
    reason: str = Field(..., description="检测理由说明")
    latency_ms: int = Field(..., ge=0, description="检测耗时(毫秒)")


# ---------- 融合与响应模型 ----------


class FusionResult(BaseModel):
    """风险融合结果。"""

    final_risk_score: float = Field(..., ge=0, le=1, description="最终风险评分")
    risk_level: RiskLevel = Field(..., description="风险等级")
    is_safe: bool = Field(..., description="是否安全通过")
    weights: Dict[str, float] = Field(
        default={"knowledge": 0.3, "retrieval": 0.3, "generation": 0.4},
        description="融合权重",
    )


class QueryResponse(BaseModel):
    """查询响应（主响应模型）。"""

    query: str = Field(..., description="原始查询")
    answer: Optional[str] = Field(
        default=None,
        description="生成回答（SAFE/WARNING 时返回；DANGER 时绝对为 null）",
    )
    is_safe: bool = Field(..., description="是否安全通过")
    risk_level: RiskLevel = Field(..., description="风险等级")
    final_risk_score: float = Field(..., description="最终风险评分 0.0~1.0")

    # 延迟拆分（Q2 答案）：检测延迟不含 LLM 生成耗时
    detection_latency_ms: int = Field(..., ge=0, description="安全检测系统耗时(毫秒): Layer2 + Layer3 NLI + 融合")
    generation_latency_ms: Optional[int] = Field(
        default=None, ge=0, description="LLM 生成耗时(毫秒), 仅当 generate_answer=true 时有值"
    )
    total_latency_ms: int = Field(..., ge=0, description="全链路总耗时(毫秒) = detection + generation")

    # 三层详情
    layer1: Optional[Layer1Result] = Field(default=None, description="知识库层结果")
    layer2: Optional[Layer2Result] = Field(default=None, description="检索层结果")
    layer3: Optional[Layer3Result] = Field(default=None, description="生成层结果")

    # 融合信息
    fusion: FusionResult = Field(..., description="融合结果")

    # 响应动作
    action: str = Field(..., description="响应动作: pass|pass_with_warning|block")
    warning_message: Optional[str] = Field(default=None, description="警告/阻断提示信息")

    # 演示对比字段（Q4 答案）：危险时展示"原本想说什么"
    blocked_answer: Optional[str] = Field(
        default=None,
        description="被阻断的原始生成内容（action=block 时用于对比展示；其他等级始终为 null）",
    )


class KBUploadResponse(BaseModel):
    """知识库上传响应。"""

    kb_id: str = Field(..., description="知识库 ID")
    inserted_count: int = Field(..., description="成功插入文档数")
    suspicious_count: int = Field(..., description="可疑文档数")
    suspicious_docs: List[Document] = Field(default=[], description="可疑文档列表")
    scan_latency_ms: int = Field(..., description="Layer1 扫描耗时(毫秒)")
    message: str = Field(..., description="操作结果描述")


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str = Field(default="ok", description="服务状态")
    version: str = Field(default="1.0.0", description="版本号")
    models_loaded: Dict[str, bool] = Field(default={}, description="模型加载状态")
    uptime_seconds: int = Field(..., description="运行时间(秒)")
