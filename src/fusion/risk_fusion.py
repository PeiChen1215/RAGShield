"""
模块名: src/fusion/risk_fusion.py
职责: 三层风险加权融合，生成最终风险评分与响应决策。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from typing import Dict, Optional, Tuple

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

    def fuse_with_prior(
        self,
        risk_score_1: float,
        risk_score_2: float,
        risk_score_3: float,
        layer1_details: Optional[Dict] = None,
    ) -> Tuple[float, RiskLevel, str, str, Dict[str, float]]:
        """带风险传导的融合策略。

        核心规则：
        1. L1 的先验知识影响 L2 的敏感度（L1 >= 0.5 时 L2 放大 2 倍）。
        2. L1 检测到指令劫持关键词时，L3 权重提升，L1/L2 降低。
        3. 任意单层达到 danger_threshold 直接阻断，不走加权。

        Args:
            risk_score_1: Layer1 风险分。
            risk_score_2: Layer2 风险分。
            risk_score_3: Layer3 风险分。
            layer1_details: Layer1 详情字典，包含 suspicious_docs 等。

        Returns:
            (final_risk_score, risk_level, action, warning_message, weights)
        """
        weights = dict(self.weights)  # 默认 0.3/0.3/0.4
        adjusted_risk_score_2 = risk_score_2

        # === 规则1：L1 已标记高危 → L2 敏感度提升 ===
        if risk_score_1 >= 0.5:
            adjusted_risk_score_2 = min(risk_score_2 * 2.0, 1.0)

        # === 规则2：L1 发现指令劫持模式 → L3 权重提升 ===
        layer1_has_instruction_pattern = False
        if layer1_details and "suspicious_docs" in layer1_details:
            for doc in layer1_details.get("suspicious_docs", []):
                text = doc.get("text", "")
                if any(kw in text for kw in ["忽略", "执行", "发送", "覆盖"]):
                    layer1_has_instruction_pattern = True
                    break

        if layer1_has_instruction_pattern:
            # L3 权重提升到 0.5，L1/L2 各降到 0.25
            weights = {"knowledge": 0.25, "retrieval": 0.25, "generation": 0.5}

        # === 规则3：任意单层达到 danger_threshold，直接阻断 ===
        if risk_score_1 >= self.danger_threshold or risk_score_3 >= self.danger_threshold:
            return (
                1.0,
                RiskLevel.DANGER,
                "block",
                f"单层高风险直接阻断: L1={risk_score_1:.2f}, L3={risk_score_3:.2f}",
                weights,
            )

        final_score = (
            weights["knowledge"] * risk_score_1
            + weights["retrieval"] * adjusted_risk_score_2
            + weights["generation"] * risk_score_3
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

        return final_score, level, action, message, weights
