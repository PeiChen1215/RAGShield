"""
模块名: tests/test_api.py
职责: API 集成测试。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.fixture
async def async_client():
    """异步 HTTP 客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpoint:
    """/health 端点测试。"""

    @pytest.mark.asyncio
    async def test_health_ok(self, async_client):
        """健康检查应返回 ok。"""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "models_loaded" in data


class TestQueryEndpoint:
    """/query 端点测试。"""

    @pytest.mark.asyncio
    async def test_query_placeholder(self, async_client):
        """查询端点应返回占位响应。"""
        payload = {
            "query": "年假有多少天",
            "kb_id": "default",
            "top_k": 5,
            "generate_answer": True,
        }
        response = await async_client.post("/api/v1/query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "年假有多少天"
        assert "final_risk_score" in data
        assert "layer1" in data
        assert "layer2" in data
        assert "layer3" in data
