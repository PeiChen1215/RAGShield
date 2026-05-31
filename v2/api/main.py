"""
v2/api/main.py
RAGShield V2 FastAPI 入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from v2.api.routers import query, kb

app = FastAPI(
    title="RAGShield V2 API",
    description="RAG 系统安全中间件 — 七层纵深防御架构",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, prefix="/api/v2/query", tags=["Query"])
app.include_router(kb.router, prefix="/api/v2/kb", tags=["Knowledge Base"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
