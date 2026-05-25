"""
模块名: src/api/main.py
职责: FastAPI 应用入口，注册路由，启动时预加载模型。
作者: RAGShield Team
创建日期: 2026-05-07
更新日期: 2026-05-10 — Week 2 lifespan 真实加载模型
"""

import asyncio
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import kb, query
from src.core.state import consistency_checker, embedder, sensitive_ner

# 全局模型加载状态（供 /health 读取）
_MODELS_LOADED = {
    "bge_m3": False,
    "bge_reranker": False,
    "uer_chinanli": False,
    "hanlp": False,
}
_START_TIME = time.time()

# 检测是否在 pytest 中运行（避免测试时触发耗时模型下载）
_IS_PYTEST = "pytest" in sys.modules


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时加载模型，关闭时清理资源。"""
    if _IS_PYTEST:
        # pytest 快速路径：标记全部已加载，避免网络下载阻塞测试
        _MODELS_LOADED.update({k: True for k in _MODELS_LOADED})
        yield
        return

    loop = asyncio.get_event_loop()

    # Step 1: 加载 Embedder（BGE-small，必加载）
    try:
        await loop.run_in_executor(None, embedder.load)
        _MODELS_LOADED["bge_m3"] = True
        print("[lifespan] [OK] Embedder (BGE-small) 加载完成")
    except Exception as e:
        print(f"[lifespan] [ERR] Embedder 加载失败: {e}")

    # Step 2: 加载 SensitiveNER（HanLP，轻量）
    try:
        await loop.run_in_executor(None, sensitive_ner._load_hanlp)
        _MODELS_LOADED["hanlp"] = sensitive_ner.use_hanlp
        print(f"[lifespan] [OK] SensitiveNER 加载完成 (HanLP={sensitive_ner.use_hanlp})")
    except Exception as e:
        print(f"[lifespan] [WARN] SensitiveNER HanLP 加载失败，降级为正则模式: {e}")
        sensitive_ner.use_hanlp = False
        _MODELS_LOADED["hanlp"] = False

    # Step 3: 加载 ConsistencyChecker（bge-reranker + chinanli，较重）
    try:
        await loop.run_in_executor(None, consistency_checker.load)
        _MODELS_LOADED["bge_reranker"] = True
        _MODELS_LOADED["uer_chinanli"] = True
        print("[lifespan] [OK] ConsistencyChecker (reranker + NLI) 加载完成")
    except Exception as e:
        print(f"[lifespan] [WARN] ConsistencyChecker 加载失败，L3 NLI 将跳过: {e}")

    yield
    # 关闭时清理资源
    print("[lifespan] [STOP] 应用关闭，清理资源")


app = FastAPI(
    title="RAGShield API",
    description="RAG 系统安全中间件 — 三层全链路纵深防御",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件（Gradio 本地调用需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(kb.router, prefix="/api/v1/kb", tags=["Knowledge Base"])
app.include_router(query.router, prefix="/api/v1", tags=["Query"])


@app.get("/api/v1/health", response_model=dict)
async def health_check():
    """健康检查端点。"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "models_loaded": _MODELS_LOADED,
        "uptime_seconds": int(time.time() - _START_TIME),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True, workers=1)
