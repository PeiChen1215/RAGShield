"""
模块名: tests/test_fusion.py
职责: 融合模块单元测试。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import pytest

from src.api.schemas import RiskLevel
from src.fusion.risk_fusion import RiskFusion


class TestRiskFusion:
    """RiskFusion 单元测试。"""

    def test_safe_threshold(self):
        """低分应判定为 SAFE。"""
        fusion = RiskFusion()
        score, level, action, msg = fusion.fuse(0.1, 0.05, 0.1)
        assert level == RiskLevel.SAFE
        assert action == "pass"

    def test_danger_threshold(self):
        """高分应判定为 DANGER。"""
        fusion = RiskFusion()
        score, level, action, msg = fusion.fuse(0.8, 0.6, 0.9)
        assert level == RiskLevel.DANGER
        assert action == "block"

    def test_warning_threshold(self):
        """中分应判定为 WARNING。"""
        fusion = RiskFusion()
        score, level, action, msg = fusion.fuse(0.2, 0.4, 0.3)
        assert level == RiskLevel.WARNING
        assert action == "pass_with_warning"

    def test_score_capped_at_1(self):
        """最终分数不应超过 1.0。"""
        fusion = RiskFusion()
        score, _, _, _ = fusion.fuse(1.0, 1.0, 1.0)
        assert score <= 1.0
