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
from src.fusion.risk_fusion import RiskFusion
from src.layer3_generation.behavior_auditor import BehaviorAuditor

router = APIRouter()

# 初始化行为审计器（轻量级，无需懒加载）
_behavior_auditor = BehaviorAuditor()
# 初始化风险融合器
_risk_fusion = RiskFusion()


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
    # 但 L3 行为审计已串联，用于演示对抗指令注入的检测能力

    generated_answer = "占位回答：系统正在开发中"

    # ---------- L3: 行为审计（已串联，对抗指令注入） ----------
    behavior_score, behavior_rules, behavior_reason = _behavior_auditor.audit(
        generated_answer
    )

    # NLI 风险映射（占位，待 consistency_checker 接入后替换）
    nli_decision = "skipped"
    nli_risk_mapped = 0.0

    # 行为风险分直接参与 L3 风险评分（取最大值）
    layer3_risk_score = max(nli_risk_mapped, behavior_score)

    # 如果行为审计触发高危，强制阻断
    layer3_reason = "占位：Layer3 待实现"
    if behavior_score >= 0.5:
        layer3_reason = f"行为审计触发: {behavior_reason}"

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
        risk_score=layer3_risk_score,
        is_anomaly=layer3_risk_score >= 0.3,
        generated_answer=generated_answer,
        consistency=ConsistencyDetail(
            reranker_score=0.0,
            nli_label="skipped",
            final_decision=nli_decision,
        ),
        detection_method="behavior_audit" if behavior_rules else "placeholder",
        reason=layer3_reason,
        latency_ms=0,
    )

    # ---------- 风险融合（带风险传导） ----------
    layer1_details = {"suspicious_docs": [doc.model_dump() for doc in layer1.suspicious_docs]}
    final_score, risk_level, action, warning_message, weights = _risk_fusion.fuse_with_prior(
        risk_score_1=layer1.risk_score,
        risk_score_2=layer2.risk_score,
        risk_score_3=layer3.risk_score,
        layer1_details=layer1_details,
    )

    is_safe = action != "block"
    fusion = FusionResult(
        final_risk_score=final_score,
        risk_level=risk_level,
        is_safe=is_safe,
        weights=weights,
    )

    return QueryResponse(
        query=request.query,
        answer=generated_answer if is_safe else None,
        is_safe=is_safe,
        risk_level=risk_level,
        final_risk_score=final_score,
        detection_latency_ms=0,
        generation_latency_ms=None,
        total_latency_ms=0,
        layer1=layer1,
        layer2=layer2,
        layer3=layer3,
        fusion=fusion,
        action=action,
        warning_message=warning_message if action == "pass_with_warning" else None,
        blocked_answer=generated_answer if action == "block" else None,
    )
