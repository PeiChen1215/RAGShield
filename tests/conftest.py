"""
模块名: tests/conftest.py
职责: pytest 共享 fixture。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import numpy as np
import pytest


@pytest.fixture
def normal_embeddings():
    """正常文档嵌入（高斯分布，50 篇 x 512 维）。"""
    np.random.seed(42)
    return np.random.randn(50, 512).astype(np.float32)


@pytest.fixture
def poisoned_embeddings():
    """含投毒文档的嵌入（最后 3 条明显偏离）。"""
    np.random.seed(42)
    normal = np.random.randn(47, 512).astype(np.float32)
    poisoned = np.random.randn(3, 512).astype(np.float32) + 5.0
    return np.vstack([normal, poisoned])


@pytest.fixture
def sample_query_request():
    """示例查询请求。"""
    return {
        "query": "公司密码策略是什么",
        "kb_id": "test_kb",
        "top_k": 5,
        "generate_answer": True,
    }
