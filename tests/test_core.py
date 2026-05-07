"""
模块名: tests/test_core.py
职责: core 模块单元测试。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import numpy as np
import pytest

from src.core.embedder import Embedder
from src.core.vector_store import VectorStore


class TestEmbedder:
    """Embedder 单元测试。"""

    def test_embed_shape(self):
        """嵌入输出维度应正确。"""
        # TODO: Week 2 实现（需要预下载模型）
        pytest.skip("需要预下载模型")


class TestVectorStore:
    """VectorStore 单元测试。"""

    def test_collection_name(self):
        """collection 命名应符合规范。"""
        store = VectorStore(persist_dir="./tests/data/chroma_db")
        assert store._collection_name("demo") == "ragshield_kb_demo"
