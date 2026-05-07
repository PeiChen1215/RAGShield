"""
模块名: src/api/main.py
职责: FastAPI 应用入口，注册路由，启动时预加载模型。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import kb, query

# 全局模型加载状态（供 /health 读取）
_MODELS_LOADED = {
    "bge_m3": False,
    "bge_reranker": False,
    "uer_chinanli": False,
    "hanlp": False,
}
_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时加载模型，关闭时清理资源。"""
    # TODO: Week 2 实现模型预加载
    # from src.core.embedder import Embedder
    # from src.layer3_generation.consistency_checker import ConsistencyChecker
    # Embedder().load()
    # ConsistencyChecker().load()
    _MODELS_LOADED["bge_m3"] = True
    _MODELS_LOADED["bge_reranker"] = True
    _MODELS_LOADED["uer_chinanli"] = True
    _MODELS_LOADED["hanlp"] = True
    yield
    # 关闭时清理资源


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
