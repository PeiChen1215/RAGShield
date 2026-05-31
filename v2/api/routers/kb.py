"""
v2/api/routers/kb.py
知识库上传路由 — 调用 v2.layer1_kb_guard.DocumentSafetyChecker
"""
import time
import traceback
from typing import Dict

from fastapi import APIRouter

from v2.api.schemas import KBUploadRequest, KBUploadResponse, KBUploadResult
from v2.layer1_kb_guard.checker import DocumentSafetyChecker

router = APIRouter()

# 按 kb_id 隔离的 checker 缓存（避免跨知识库污染）
_checker_cache: Dict[str, DocumentSafetyChecker] = {}


def _get_checker(kb_id: str) -> DocumentSafetyChecker:
    """获取或创建指定 kb_id 的 checker，隔离不同知识库的状态。"""
    if kb_id not in _checker_cache:
        _checker_cache[kb_id] = DocumentSafetyChecker()
    return _checker_cache[kb_id]


@router.post("/upload", response_model=KBUploadResponse)
async def upload_documents(request: KBUploadRequest):
    """上传文档到知识库，自动触发 Layer1 四检测器并联扫描。"""
    t0 = time.time()
    kb_id = request.kb_id or "default"
    checker = _get_checker(kb_id)
    
    results = []
    passed = blocked = review = 0
    
    for doc in request.documents:
        try:
            result = checker.check(doc.text, doc.doc_id, doc.metadata)
        except Exception as e:
            traceback.print_exc()
            # 检测失败时保守处理：标记为 review
            from v2.interfaces import CheckResult, Action
            result = CheckResult(
                action=Action.REVIEW,
                risk_score=0.5,
                reason=f"检测过程异常: {str(e)[:100]}",
            )
        
        results.append(KBUploadResult(
            doc_id=doc.doc_id,
            action=result.action.value,
            risk_score=result.risk_score,
            reason=result.reason,
        ))
        
        if result.action.value == "pass":
            passed += 1
            checker.add_kb_reference(doc.text, doc.doc_id)
        elif result.action.value == "block":
            blocked += 1
        else:
            review += 1
    
    return KBUploadResponse(
        kb_id=kb_id,
        total=len(request.documents),
        passed=passed,
        blocked=blocked,
        review=review,
        results=results,
        latency_ms=int((time.time() - t0) * 1000),
    )
