"""
模块名: src/api/routers/kb.py
职责: 知识库管理路由（/kb/upload, /kb/scan）。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from fastapi import APIRouter

from src.api.schemas import KBUploadRequest, KBUploadResponse

router = APIRouter()


@router.post("/upload", response_model=KBUploadResponse)
async def upload_documents(request: KBUploadRequest):
    """上传文档到知识库，可选自动触发 Layer1 扫描。

    Args:
        request: 上传请求，包含文档列表和配置。

    Returns:
        KBUploadResponse: 上传结果，包含可疑文档列表。
    """
    # TODO: Week 2 实现
    return KBUploadResponse(
        kb_id=request.kb_id or "default",
        inserted_count=len(request.documents),
        suspicious_count=0,
        suspicious_docs=[],
        scan_latency_ms=0,
        message="占位：知识库上传接口待实现",
    )


@router.get("/scan")
async def scan_knowledge_base(kb_id: str = "default"):
    """触发 Layer1 重新扫描已有知识库。

    Args:
        kb_id: 目标知识库 ID。

    Returns:
        扫描结果摘要。
    """
    # TODO: Week 2 实现
    return {
        "kb_id": kb_id,
        "total_docs": 0,
        "suspicious_count": 0,
        "suspicious_docs": [],
        "scan_latency_ms": 0,
        "message": "占位：Layer1 扫描接口待实现",
    }
