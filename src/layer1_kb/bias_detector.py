"""
模块名: src/layer1_kb/bias_detector.py
职责: 情感极性检测 — V1 占位，V2 完整实现。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from typing import Dict


class BiasDetector:
    """偏见检测器 — V1 占位。"""

    def detect(self, text: str) -> Dict:
        """检测文档中的偏见倾向。

        Args:
            text: 待检测文本。

        Returns:
            检测结果字典。
        """
        return {
            "detected": False,
            "confidence": 0.0,
            "risk_score": 0.0,
            "reason": "V1 占位: 偏见检测模块已预留，V2 实现完整逻辑",
        }
