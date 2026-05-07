"""
模块名: src/layer2_retrieval/relevance_scorer.py
职责: 查询-文档余弦相似度计算。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import numpy as np


class RelevanceScorer:
    """相关性评分器。"""

    @staticmethod
    def compute_similarity(query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
        """计算查询与文档集合的余弦相似度。

        Args:
            query_embedding: 查询向量 (D,)。
            doc_embeddings: 文档矩阵 (N x D)。

        Returns:
            np.ndarray: 相似度分数 (N,)，范围 [-1, 1]，通常已归一化为 [0, 1]。
        """
        # 向量已 L2 归一化，点积即余弦相似度
        return np.dot(doc_embeddings, query_embedding)
