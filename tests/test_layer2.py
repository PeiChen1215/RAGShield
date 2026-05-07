"""
模块名: tests/test_layer2.py
职责: Layer2 单元测试。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import numpy as np
import pytest

from src.layer2_retrieval.attention_analyzer import AttentionAnalyzer


class TestAttentionAnalyzer:
    """AttentionAnalyzer 单元测试。"""

    def test_normal_distribution_low_risk(self):
        """均匀分布应返回低风险。"""
        analyzer = AttentionAnalyzer()
        scores = [0.90, 0.85, 0.80, 0.75, 0.70]
        result = analyzer.analyze(scores, set(), [f"doc_{i}" for i in range(5)])
        assert result["risk_score"] < 0.3
        assert not result["is_anomaly"]

    def test_skewed_distribution_high_risk(self):
        """极度不均匀分布应返回高风险。"""
        analyzer = AttentionAnalyzer()
        scores = [0.99, 0.50, 0.40, 0.30, 0.20]
        result = analyzer.analyze(scores, set(), [f"doc_{i}" for i in range(5)])
        assert result["is_anomaly"]

    def test_suspicious_relay_bonus(self):
        """可疑文档接力加分应生效。"""
        analyzer = AttentionAnalyzer()
        scores = [0.90, 0.85, 0.80, 0.75, 0.70]
        doc_ids = ["doc_0", "doc_1", "doc_2", "doc_3", "doc_4"]
        suspicious_ids = {"doc_1", "doc_3"}
        result = analyzer.analyze(scores, suspicious_ids, doc_ids)
        assert result["suspicious_doc_count"] == 2
        assert result["risk_score"] > 0.3
