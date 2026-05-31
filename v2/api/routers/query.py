"""
v2/api/routers/query.py
查询检测路由 — 调用 v2.pipeline.RAGShieldPipeline
"""
import time
import traceback
from typing import List

from fastapi import APIRouter

from v2.api.schemas import QueryRequest, QueryResponse
from v2.pipeline import RAGShieldPipeline

router = APIRouter()

# 全局 Pipeline 实例（懒加载）
_pipeline: RAGShieldPipeline = None


def _get_pipeline() -> RAGShieldPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGShieldPipeline()
    return _pipeline


@router.post("/detect", response_model=QueryResponse)
async def query_detect(request: QueryRequest):
    """提交查询 + 检索文档，执行全链路七层检测。"""
    t0 = time.time()
    pipeline = _get_pipeline()
    
    try:
        # 执行全链路（自动检索文档）
        result = pipeline.process_query(
            query=request.query,
            skip_layer0=request.skip_layer0,
        )
    except Exception as e:
        # 任何异常都返回降级响应，而非 500
        trace = traceback.format_exc()
        print(f"[ERROR] Pipeline execution failed: {e}\n{trace}")
        return QueryResponse(
            query=request.query,
            action="review",
            risk_level="warning",
            final_risk_score=0.5,
            answer="[系统内部错误，已降级处理] 请稍后重试或联系管理员。",
            warning_message="检测到系统异常，回答可能不完整。",
            latency_ms=int((time.time() - t0) * 1000),
            trace_id="error",
        )
    
    # 构建 Layer0 响应
    layer0_resp = None
    if result.layer0_result:
        from v2.api.schemas import Layer0Result
        layer0_resp = Layer0Result(
            blocked=result.layer0_result.blocked,
            risk_score=result.layer0_result.risk_score,
            risk_level=result.layer0_result.risk_level.value,
            triggered_rules=result.layer0_result.triggered_rules,
            reason=result.layer0_result.reason,
        )
    
    # 构建 Layer3 事实列表
    facts_resp = []
    for f in result.layer3_facts:
        from v2.api.schemas import FactItem
        facts_resp.append(FactItem(
            type=f.type.value,
            content=f.content,
            source_doc_id=f.source_doc_id,
            confidence=f.confidence,
            risk_level=f.risk_level,
            risk_reason=f.risk_reason,
        ))
    
    # 构建 Layer4 审计结果
    layer4_resp = None
    if result.layer4_audit:
        from v2.api.schemas import Layer4Result, ConflictItem
        conflicts = []
        for c in result.layer4_audit.conflicts:
            conflicts.append(ConflictItem(
                conflict_type=c.conflict_type,
                topic=c.topic,
                description=c.description,
                severity=c.severity,
            ))
        layer4_resp = Layer4Result(
            verified_facts_count=len(result.layer4_audit.verified_facts),
            unverified_facts_count=len(result.layer4_audit.unverified_facts),
            conflicts=conflicts,
            overall_risk=result.layer4_audit.overall_risk,
            reason=result.layer4_audit.reason,
        )
    
    # 构建 Layer6 审计结果
    layer6_is_safe = True
    layer6_risk_score = 0.0
    if result.layer6_audit:
        layer6_is_safe = result.layer6_audit.is_safe
        layer6_risk_score = result.layer6_audit.risk_score
    
    # 构建融合结果
    fusion_resp = None
    if result.fusion_result:
        from v2.api.schemas import FusionResult
        fusion_resp = FusionResult(
            final_score=result.fusion_result.final_score,
            triggered_layers=result.fusion_result.triggered_layers,
            reason=result.fusion_result.reason,
        )
    
    # 最终响应
    decision = result.final_decision
    return QueryResponse(
        query=request.query,
        action=decision.action.value if decision else "pass",
        risk_level="danger" if (decision and decision.action.value == "block") else "warning" if (decision and decision.action.value == "review") else "safe",
        final_risk_score=result.fusion_result.final_score if result.fusion_result else 0.0,
        answer=decision.answer if decision else None,
        warning_message=decision.warning if decision else None,
        layer0=layer0_resp,
        layer2_risky_doc_count=len(result.layer2_result.risky_docs) if result.layer2_result else 0,
        layer3_facts=facts_resp,
        layer4=layer4_resp,
        layer6_is_safe=layer6_is_safe,
        layer6_risk_score=layer6_risk_score,
        fusion=fusion_resp,
        latency_ms=result.latency_ms,
        trace_id=result.trace_id,
    )
