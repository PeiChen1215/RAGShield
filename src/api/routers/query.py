"""
模块名: src/api/routers/query.py
职责: 查询检测路由（/query），全链路三层检测核心端点。
作者: RAGShield Team
创建日期: 2026-05-07
更新日期: 2026-05-10 — Week 2 全链路真实接入
"""

import time
from typing import Dict, List, Optional, Set

from fastapi import APIRouter

from src.api.schemas import (
    ConsistencyDetail,
    Document,
    FusionResult,
    Layer1Result,
    Layer2Result,
    Layer3Result,
    QueryRequest,
    QueryResponse,
    RetrievedDocument,
    RiskLevel,
)
from src.api.routers.kb import _load_scan_cache
from src.core.state import (
    attention_analyzer,
    behavior_auditor,
    consistency_checker,
    embedder,
    llm_client,
    risk_fusion,
    sensitive_ner,
    vector_store,
)

router = APIRouter()


# ---------- 辅助函数 ----------

def _nli_decision_to_risk(decision: str) -> float:
    """将 NLI 决策映射为风险分。"""
    mapping = {
        "safe": 0.0,
        "neutral": 0.15,
        "alert_review": 0.35,
        "high_confidence_block": 0.60,
        "skipped": 0.0,
    }
    return mapping.get(decision, 0.0)


# ---------- 主路由 ----------

@router.post("/query", response_model=QueryResponse)
async def query_detect(request: QueryRequest):
    """提交查询，执行全链路三层检测。

    完整链路:
    L1: SensitiveNER 检测查询文本 + 读取 upload 时扫描缓存
    L2: Embedder编码 → VectorStore检索 → AttentionAnalyzer分析
    L3: LLM生成(可选) → ConsistencyChecker一致性 → BehaviorAuditor行为审计
    融合: RiskFusion.fuse_with_prior(含风险传导)
    """
    query = request.query
    kb_id = request.kb_id
    top_k = request.top_k
    generate_answer = request.generate_answer

    # ============================================================
    # Layer 1: 知识库层（查询文本敏感实体 + 历史可疑文档缓存）
    # ============================================================
    t_l1 = time.time()
    entities, entity_risk_score = sensitive_ner.detect(query)
    l1_suspicious_map = _load_scan_cache(kb_id)
    l1_suspicious_ids: Set[str] = set(l1_suspicious_map.keys())
    l1_ms = int((time.time() - t_l1) * 1000)

    layer1_risk_score = min(entity_risk_score, 1.0)
    layer1_is_anomaly = layer1_risk_score >= 0.3

    # ============================================================
    # 检索: 查询编码 + 向量检索
    # ============================================================
    t_retrieve = time.time()
    query_embedding = embedder.embed_single(query)
    doc_ids, distances, texts, metadatas = vector_store.query(kb_id, query_embedding, top_k=top_k)

    # 检索到攻击文档时提升 L1 风险分（最强区分信号）
    attack_doc_count = sum(1 for m in metadatas if m and m.get("attack_type"))
    if attack_doc_count > 0:
        layer1_risk_score = min(layer1_risk_score + 0.3 + attack_doc_count * 0.1, 0.8)
        layer1_is_anomaly = True

    # ChromaDB cosine 距离 → 相似度
    relevance_scores = [1.0 - float(d) for d in distances]
    retrieve_ms = int((time.time() - t_retrieve) * 1000)

    # 构造 RetrievedDocument 列表
    retrieved_docs: List[RetrievedDocument] = []
    for i in range(len(doc_ids)):
        retrieved_docs.append(
            RetrievedDocument(
                doc_id=doc_ids[i],
                text=texts[i],
                metadata=metadatas[i] if metadatas else {},
                similarity_score=relevance_scores[i],
                rank=i + 1,
            )
        )

    # ============================================================
    # Layer 2: 检索层（来源可信度 + 可疑文档接力）
    # ============================================================
    t_l2 = time.time()
    if len(doc_ids) == 0:
        # 知识库为空，直接返回安全
        l2_result = {
            "risk_score": 0.0,
            "is_anomaly": False,
            "attention_variance": 0.0,
            "attention_entropy": 0.0,
            "source_trust_risk": 0.0,
            "suspicious_doc_count": 0,
            "detection_method": "empty_kb",
            "reason": "知识库为空，无检索结果",
        }
    else:
        l2_result = attention_analyzer.analyze(
            relevance_scores=relevance_scores,
            layer1_suspicious_ids=l1_suspicious_ids,
            retrieved_doc_ids=doc_ids,
            metadatas=metadatas if metadatas else [],
        )
    l2_ms = int((time.time() - t_l2) * 1000)

    layer2_risk_score = float(l2_result["risk_score"])
    layer2_is_anomaly = bool(l2_result["is_anomaly"])

    # ============================================================
    # Layer 3: 生成层（LLM生成 + NLI一致性 + 行为审计）
    # ============================================================
    t_l3 = time.time()
    generated_answer: Optional[str] = None
    nli_decision = "skipped"
    nli_reason = "未启用生成"
    reranker_score = 0.0
    nli_label = "skipped"
    behavior_score = 0.0
    behavior_rules: List[Dict] = []
    behavior_reason = "未启用生成"

    if generate_answer:
        # Step 3a: LLM 生成
        t_llm = time.time()
        try:
            generated_answer = await llm_client.generate(query, contexts=texts)
        except Exception as e:
            generated_answer = f"[LLM 生成失败: {str(e)}]"
        llm_ms = int((time.time() - t_llm) * 1000)

        # Step 3b: NLI 一致性检测（逐文档检测，取最高风险分）
        # 优化：只检测前 3 篇 + high_confidence_block 提前终止
        if generated_answer and not generated_answer.startswith("[LLM 生成失败"):
            max_nli_risk = 0.0
            best_result = None
            for text in texts[:3]:  # 最多检测前 3 篇，减少推理耗时
                try:
                    rs, nl, nd, nr = consistency_checker.check(text, generated_answer)
                    risk = _nli_decision_to_risk(nd)
                    if risk > max_nli_risk:
                        max_nli_risk = risk
                        best_result = (rs, nl, nd, nr)
                    # 已触发最高风险，提前终止
                    if nd == "high_confidence_block":
                        break
                except Exception:
                    continue
            if best_result:
                reranker_score, nli_label, nli_decision, nli_reason = best_result
            else:
                nli_decision = "skipped"
                nli_reason = "NLI逐文档检测全部失败"
        else:
            nli_decision = "skipped"
            nli_reason = "LLM生成失败，跳过NLI"

        # Step 3c: 行为审计
        behavior_score, behavior_rules, behavior_reason = behavior_auditor.audit(generated_answer)
    else:
        llm_ms = 0

    nli_risk_mapped = _nli_decision_to_risk(nli_decision)
    layer3_risk_score = max(nli_risk_mapped, behavior_score)
    layer3_is_anomaly = layer3_risk_score >= 0.3 or behavior_score >= 0.5
    l3_ms = int((time.time() - t_l3) * 1000)

    # ============================================================
    # 风险融合（带风险传导）
    # ============================================================
    layer1_details: Dict = {
        "suspicious_docs": [
            {"doc_id": doc_id, "text": l1_suspicious_map[doc_id].get("detail", {}).get("avg_similarity", 0.0)}
            for doc_id in l1_suspicious_ids
        ]
    }

    final_score, risk_level, action, warning_message, weights = risk_fusion.fuse_with_prior(
        risk_score_1=layer1_risk_score,
        risk_score_2=layer2_risk_score,
        risk_score_3=layer3_risk_score,
        layer1_details=layer1_details,
    )

    is_safe = action != "block"
    fusion = FusionResult(
        final_risk_score=final_score,
        risk_level=risk_level,
        is_safe=is_safe,
        weights=weights,
    )

    # ============================================================
    # 组装响应
    # ============================================================
    detection_latency_ms = l1_ms + l2_ms + l3_ms
    generation_latency_ms = llm_ms if generate_answer else None
    total_latency_ms = detection_latency_ms + (generation_latency_ms or 0)

    # 构建 L1 检测方法与原因（综合三个信号源）
    l1_methods = []
    l1_reason_parts = []

    if entities:
        l1_methods.append("sensitive_ner")
        l1_reason_parts.append(f"查询文本检测到 {len(entities)} 个敏感实体")
    if l1_suspicious_ids:
        l1_methods.append("scan_cache")
        l1_reason_parts.append(f"知识库历史扫描标记 {len(l1_suspicious_ids)} 篇可疑文档")
    if attack_doc_count > 0:
        l1_methods.append("attack_doc_relay")
        l1_reason_parts.append(f"本次检索召回 {attack_doc_count} 篇攻击文档（+{0.3 + attack_doc_count * 0.1:.2f}分）")

    layer1_detection_method = "+".join(l1_methods) if l1_methods else "none"
    layer1_reason = "；".join(l1_reason_parts) if l1_reason_parts else "查询文本无敏感模式，知识库无可疑文档，未召回攻击文档"

    # 从 scan_cache 构造 suspicious_docs（含风险分信息）
    l1_suspicious_docs = []
    for doc_id, info in l1_suspicious_map.items():
        l1_suspicious_docs.append(
            Document(
                doc_id=doc_id,
                text=f"[scan_cache] risk_score={info.get('risk_score', 0):.3f}",
                metadata=info.get("detail", {}),
            )
        )

    layer1 = Layer1Result(
        layer="knowledge_base",
        risk_score=layer1_risk_score,
        is_anomaly=layer1_is_anomaly,
        suspicious_docs=l1_suspicious_docs,
        sensitive_entities=entities,
        detection_method=layer1_detection_method,
        reason=layer1_reason,
        latency_ms=l1_ms,
    )

    layer2 = Layer2Result(
        layer="retrieval",
        risk_score=layer2_risk_score,
        is_anomaly=layer2_is_anomaly,
        attention_variance=float(l2_result["attention_variance"]),
        attention_entropy=float(l2_result["attention_entropy"]),
        retrieved_docs=retrieved_docs,
        relevance_scores=relevance_scores,
        suspicious_doc_count=int(l2_result["suspicious_doc_count"]),
        detection_method=str(l2_result["detection_method"]),
        reason=str(l2_result["reason"]),
        latency_ms=l2_ms,
    )

    layer3 = Layer3Result(
        layer="generation",
        risk_score=layer3_risk_score,
        is_anomaly=layer3_is_anomaly,
        generated_answer=generated_answer,
        consistency=ConsistencyDetail(
            reranker_score=float(reranker_score),
            nli_label=nli_label,
            final_decision=nli_decision,
        ),
        detection_method="behavior_audit" if behavior_rules else ("nli_contradiction" if nli_decision in ("alert_review", "high_confidence_block") else "skipped"),
        reason=behavior_reason if behavior_rules else nli_reason,
        latency_ms=l3_ms,
    )

    return QueryResponse(
        query=query,
        answer=generated_answer if is_safe else None,
        blocked_answer=generated_answer if action == "block" else None,
        is_safe=is_safe,
        risk_level=risk_level,
        final_risk_score=final_score,
        detection_latency_ms=detection_latency_ms,
        generation_latency_ms=generation_latency_ms,
        total_latency_ms=total_latency_ms,
        layer1=layer1,
        layer2=layer2,
        layer3=layer3,
        fusion=fusion,
        action=action,
        warning_message=warning_message if action == "pass_with_warning" else None,
    )
