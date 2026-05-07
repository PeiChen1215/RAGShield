"""
模块名: src/fusion/risk_fusion.py
职责: 三层风险加权融合，生成最终风险评分与响应决策。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from typing import Dict, Tuple

from src.api.schemas import RiskLevel


class RiskFusion:
    """风险融合器。"""

    def __init__(
        self,
        knowledge_weight: float = 0.3,
        retrieval_weight: float = 0.3,
        generation_weight: float = 0.4,
        danger_threshold: float = 0.5,
        warning_threshold: float = 0.3,
    ):
        """初始化融合器。

        Args:
            knowledge_weight: 知识库层权重。
            retrieval_weight: 检索层权重。
            generation_weight: 生成层权重。
            danger_threshold: 危险判定阈值。
            warning_threshold: 警告判定阈值。
        """
        self.weights = {
            "knowledge": knowledge_weight,
            "retrieval": retrieval_weight,
            "generation": generation_weight,
        }
        self.danger_threshold = danger_threshold
        self.warning_threshold = warning_threshold

    def fuse(
        self,
        risk_score_1: float,
        risk_score_2: float,
        risk_score_3: float,
    ) -> Tuple[float, RiskLevel, str, str]:
        """融合三层风险评分。

        Args:
            risk_score_1: Layer1 风险分。
            risk_score_2: Layer2 风险分。
            risk_score_3: Layer3 风险分。

        Returns:
            (final_risk_score, risk_level, action, warning_message)
        """
        final_score = (
            self.weights["knowledge"] * risk_score_1
            + self.weights["retrieval"] * risk_score_2
            + self.weights["generation"] * risk_score_3
        )
        final_score = min(max(final_score, 0.0), 1.0)

        if final_score >= self.danger_threshold:
            level = RiskLevel.DANGER
            action = "block"
            message = "检测到安全风险，已阻断输出，请联系管理员核实。"
        elif final_score >= self.warning_threshold:
            level = RiskLevel.WARNING
            action = "pass_with_warning"
            message = "本回答可能包含未核实的信息，请谨慎使用。"
        else:
            level = RiskLevel.SAFE
            action = "pass"
            message = ""

        return final_score, level, action, message
