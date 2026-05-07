"""
模块名: src/layer2_retrieval/attention_analyzer.py
职责: 检索结果相关性分布的方差和熵分析 + 可疑文档接力加分。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from typing import Dict, List, Set

import numpy as np
from scipy.stats import entropy


class AttentionAnalyzer:
    """注意力方差分析器（伪注意力）。"""

    def __init__(
        self,
        variance_threshold: float = 0.5,
        entropy_threshold: float = 1.0,
        suspicious_bonus: float = 0.15,
        max_bonus: float = 0.4,
    ):
        """初始化分析器。

        Args:
            variance_threshold: 方差异常阈值。
            entropy_threshold: 熵异常阈值（低于此值表示信息集中）。
            suspicious_bonus: 单篇可疑文档加分。
            max_bonus: 可疑文档加分上限。
        """
        self.variance_threshold = variance_threshold
        self.entropy_threshold = entropy_threshold
        self.suspicious_bonus = suspicious_bonus
        self.max_bonus = max_bonus

    def analyze(
        self,
        relevance_scores: List[float],
        layer1_suspicious_ids: Set[str],
        retrieved_doc_ids: List[str],
    ) -> Dict:
        """分析检索结果分布。

        Args:
            relevance_scores: top-k 相似度分数列表（余弦相似度 0~1）。
            layer1_suspicious_ids: Layer1 已标记的可疑文档 ID 集合。
            retrieved_doc_ids: 检索结果文档 ID 列表（与 relevance_scores 一一对应）。

        Returns:
            分析结果字典，包含 risk_score, variance, entropy 等。
        """
        scores = np.array(relevance_scores)

        # 子步骤 3a: 相似度分布分析
        attn_variance = float(np.var(scores))
        # 归一化到概率分布后计算熵
        prob = scores / (np.sum(scores) + 1e-6)
        attn_entropy = float(entropy(prob))

        is_variance_anomaly = attn_variance > self.variance_threshold
        is_entropy_anomaly = attn_entropy < self.entropy_threshold
        base_score = 0.5 if (is_variance_anomaly or is_entropy_anomaly) else 0.05

        # 子步骤 3b: 可疑文档接力加分（纵深协同）
        bonus = 0.0
        suspicious_count = 0
        for doc_id in retrieved_doc_ids:
            if doc_id in layer1_suspicious_ids:
                bonus += self.suspicious_bonus
                suspicious_count += 1
        bonus = min(bonus, self.max_bonus)

        risk_score = min(base_score + bonus, 1.0)
        is_anomaly = risk_score >= 0.3

        detection_method = (
            "attention_variance+suspicious_relay" if bonus > 0 else "attention_variance"
        )
        reason = (
            f"相似度分布{'异常' if is_variance_anomaly or is_entropy_anomaly else '正常'}，"
            f"检索结果中包含 {suspicious_count} 篇已标记可疑文档"
        )

        return {
            "risk_score": risk_score,
            "is_anomaly": is_anomaly,
            "attention_variance": attn_variance,
            "attention_entropy": attn_entropy,
            "suspicious_doc_count": suspicious_count,
            "detection_method": detection_method,
            "reason": reason,
        }
