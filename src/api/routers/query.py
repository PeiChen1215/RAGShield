"""
模块名: src/api/routers/query.py
职责: 查询检测路由（/query），全链路三层检测核心端点。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from fastapi import APIRouter

from src.api.schemas import (
    ConsistencyDetail,
    FusionResult,
    Layer1Result,
    Layer2Result,
    Layer3Result,
    QueryRequest,
    QueryResponse,
    RiskLevel,
)

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_detect(request: QueryRequest):
    """提交查询，执行全链路三层检测。

    Args:
        request: 查询请求。

    Returns:
        QueryResponse: 包含风险评分、生成回答、三层检测详情。
    """
    # TODO: Week 2-3 实现完整逻辑
    # 当前返回占位响应，确保接口契约正确
    layer1 = Layer1Result(
        risk_score=0.0,
        is_anomaly=False,
        suspicious_docs=[],
        sensitive_entities=[],
        detection_method="placeholder",
        reason="占位：Layer1 待实现",
        latency_ms=0,
    )
    layer2 = Layer2Result(
        risk_score=0.0,
        is_anomaly=False,
        attention_variance=0.0,
        attention_entropy=0.0,
        retrieved_docs=[],
        relevance_scores=[],
        suspicious_doc_count=0,
        detection_method="placeholder",
        reason="占位：Layer2 待实现",
        latency_ms=0,
    )
    layer3 = Layer3Result(
        risk_score=0.0,
        is_anomaly=False,
        generated_answer=None,
        consistency=ConsistencyDetail(
            reranker_score=0.0,
            nli_label="skipped",
            final_decision="skipped",
        ),
        detection_method="placeholder",
        reason="占位：Layer3 待实现",
        latency_ms=0,
    )
    fusion = FusionResult(
        final_risk_score=0.0,
        risk_level=RiskLevel.SAFE,
        is_safe=True,
    )

    return QueryResponse(
        query=request.query,
        answer="占位回答：系统正在开发中",
        is_safe=True,
        risk_level=RiskLevel.SAFE,
        final_risk_score=0.0,
        detection_latency_ms=0,
        generation_latency_ms=None,
        total_latency_ms=0,
        layer1=layer1,
        layer2=layer2,
        layer3=layer3,
        fusion=fusion,
        action="pass",
        warning_message=None,
        blocked_answer=None,
    )
