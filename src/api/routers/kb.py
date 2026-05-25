"""
模块名: src/api/routers/kb.py
职责: 知识库管理路由（/kb/upload, /kb/scan）。
作者: RAGShield Team
创建日期: 2026-05-07
更新日期: 2026-05-10 — Week 2 真实串联 Embedder + VectorStore + OutlierDetector
"""

import json
import os
import time
import uuid
from typing import Dict, List

from fastapi import APIRouter

from src.api.schemas import Document, KBUploadRequest, KBUploadResponse
from src.core.state import embedder, outlier_detector, vector_store

router = APIRouter()


# ---------- 扫描缓存（Q18 决策：JSONL 持久化，供 query.py L2 读取） ----------

def _scan_cache_path(kb_id: str) -> str:
    return f"./data/layer1_scan_cache_{kb_id}.jsonl"


def _save_scan_cache(kb_id: str, records: List[Dict]) -> None:
    """写入 Layer1 可疑文档缓存。每行一个 JSON。"""
    path = _scan_cache_path(kb_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _load_scan_cache(kb_id: str) -> Dict[str, Dict]:
    """读取缓存，返回 {doc_id: {risk_score, detail}}。"""
    path = _scan_cache_path(kb_id)
    if not os.path.exists(path):
        return {}
    result = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            result[record["doc_id"]] = {
                "risk_score": record.get("risk_score", 0.0),
                "detail": record.get("detail", {}),
            }
    return result


# ---------- 路由 ----------

@router.post("/upload", response_model=KBUploadResponse)
async def upload_documents(request: KBUploadRequest):
    """上传文档到知识库，可选自动触发 Layer1 扫描。

    流程: Embedder编码 → VectorStore入库 → OutlierDetector扫描 → 写缓存
    """
    kb_id = request.kb_id or str(uuid.uuid4())[:12]

    texts = [doc.text for doc in request.documents]
    doc_ids = [doc.doc_id for doc in request.documents]
    metadatas = [doc.metadata for doc in request.documents]

    # Step 1: 编码
    t0 = time.time()
    embeddings = embedder.embed(texts)
    embed_ms = int((time.time() - t0) * 1000)

    # Step 2: 入库
    t1 = time.time()
    vector_store.insert(kb_id, doc_ids, texts, embeddings, metadatas)
    insert_ms = int((time.time() - t1) * 1000)

    # Step 3: Layer1 扫描（可选）
    suspicious_docs: List[Document] = []
    scan_ms = 0
    if request.auto_scan:
        t2 = time.time()
        suspicious_indices, risk_scores, details = outlier_detector.detect(
            embeddings,
            texts=[doc.text for doc in request.documents],
            metadatas=metadatas,
        )
        scan_ms = int((time.time() - t2) * 1000)

        cache_records = []
        for idx in suspicious_indices:
            cache_records.append({
                "doc_id": doc_ids[idx],
                "risk_score": float(risk_scores[idx]),
                "detail": details[idx],
            })
            suspicious_docs.append(request.documents[idx])
        _save_scan_cache(kb_id, cache_records)

    return KBUploadResponse(
        kb_id=kb_id,
        inserted_count=len(request.documents),
        suspicious_count=len(suspicious_docs),
        suspicious_docs=suspicious_docs,
        scan_latency_ms=scan_ms,
        message=(
            f"上传 {len(request.documents)} 篇，"
            f"编码 {embed_ms}ms，入库 {insert_ms}ms"
            + (f"，扫描 {scan_ms}ms，检出 {len(suspicious_docs)} 篇可疑" if request.auto_scan else "，跳过扫描")
        ),
    )


@router.get("/scan")
async def scan_knowledge_base(kb_id: str = "default"):
    """触发 Layer1 重新扫描已有知识库。

    流程: VectorStore取全部 → OutlierDetector重新检测 → 更新缓存
    """
    doc_ids, embeddings, texts, metadatas = vector_store.get_all(kb_id)

    if len(doc_ids) == 0:
        return {
            "kb_id": kb_id,
            "total_docs": 0,
            "suspicious_count": 0,
            "suspicious_docs": [],
            "scan_latency_ms": 0,
            "message": "知识库为空，无需扫描",
        }

    import numpy as np

    embeddings_arr = np.array(embeddings)

    t0 = time.time()
    suspicious_indices, risk_scores, details = outlier_detector.detect(
        embeddings_arr,
        texts=texts,
        metadatas=metadatas,
    )
    scan_ms = int((time.time() - t0) * 1000)

    cache_records = []
    suspicious_doc_ids = []
    for idx in suspicious_indices:
        cache_records.append({
            "doc_id": doc_ids[idx],
            "risk_score": float(risk_scores[idx]),
            "detail": details[idx],
        })
        suspicious_doc_ids.append({
            "doc_id": doc_ids[idx],
            "text_preview": texts[idx][:100] + "..." if len(texts[idx]) > 100 else texts[idx],
        })
    _save_scan_cache(kb_id, cache_records)

    return {
        "kb_id": kb_id,
        "total_docs": len(doc_ids),
        "suspicious_count": len(suspicious_indices),
        "suspicious_docs": suspicious_doc_ids,
        "scan_latency_ms": scan_ms,
        "message": f"扫描完成，{len(doc_ids)} 篇中检出 {len(suspicious_indices)} 篇可疑",
    }
