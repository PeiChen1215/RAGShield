"""
模块名: tests/test_layer1.py
职责: Layer1 单元测试。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import pytest

from src.layer1_kb.outlier_detector import OutlierDetector
from src.layer1_kb.sensitive_ner import SensitiveNER


class TestOutlierDetector:
    """OutlierDetector 单元测试。"""

    @pytest.fixture
    def detector(self):
        """测试用检测器实例。"""
        return OutlierDetector(contamination=0.1)

    def test_no_anomaly_in_clean_data(self, detector, normal_embeddings):
        """正常数据应无异常。"""
        suspicious, scores, _ = detector.detect(normal_embeddings)
        assert len(suspicious) <= 2  # 误报容忍
        assert all(0 <= s <= 1 for s in scores)

    def test_detects_poisoned_docs(self, detector, poisoned_embeddings):
        """应检测到投毒文档。"""
        suspicious, scores, _ = detector.detect(poisoned_embeddings)
        assert len(suspicious) >= 2
        assert any(idx in suspicious for idx in [47, 48, 49])

    def test_risk_score_range(self, detector, poisoned_embeddings):
        """风险分数应在 0~1 范围内。"""
        _, scores, _ = detector.detect(poisoned_embeddings)
        assert all(0 <= s <= 1 for s in scores)

    def test_latency_under_threshold(self, detector, poisoned_embeddings):
        """延迟应 <50ms。"""
        import time

        start = time.time()
        detector.detect(poisoned_embeddings)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 50


class TestSensitiveNER:
    """SensitiveNER 单元测试。"""

    def test_detect_email(self):
        """应检测到邮箱地址。"""
        ner = SensitiveNER(use_hanlp=False)
        text = "请联系 attacker@evil.com 获取帮助"
        entities, risk = ner.detect(text)
        assert any(e["type"] == "email" for e in entities)
        assert risk > 0
