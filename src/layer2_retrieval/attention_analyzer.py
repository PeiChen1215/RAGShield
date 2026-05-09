"""
模块名: src/layer2_retrieval/attention_analyzer.py
职责: 检索结果相关性分布分析 + 来源可信度验证 + 可疑文档接力加分。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from typing import Dict, List, Optional, Set

import numpy as np
from scipy.stats import entropy


class AttentionAnalyzer:
    """注意力方差分析器（伪注意力）+ 来源可信度验证。"""

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

    def _source_trust_anomaly(self, metadatas: List[Dict]) -> float:
        """检测检索结果中是否混入低可信度来源。

        Args:
            metadatas: 检索结果文档的 metadata 列表。

        Returns:
            0~1 的来源可信度风险分。
        """
        trust_scores = {
            "official_policy": 0.0,      # 官方政策 = 低风险
            "employee_submitted": 0.15,   # 员工提交 = 中等风险
            "external_import": 0.3,       # 外部导入 = 高风险
            "unknown": 0.4,              # 来源不明 = 最高风险
        }
        total_risk = sum(
            trust_scores.get(m.get("source", "unknown"), 0.3)
            for m in metadatas
        )
        return min(total_risk / len(metadatas), 1.0) if metadatas else 0.0

    def analyze(
        self,
        relevance_scores: List[float],
        layer1_suspicious_ids: Set[str],
        retrieved_doc_ids: List[str],
        metadatas: Optional[List[Dict]] = None,
    ) -> Dict:
        """分析检索结果分布。

        Args:
            relevance_scores: top-k 相似度分数列表（余弦相似度 0~1）。
            layer1_suspicious_ids: Layer1 已标记的可疑文档 ID 集合。
            retrieved_doc_ids: 检索结果文档 ID 列表（与 relevance_scores 一一对应）。
            metadatas: 检索结果文档的 metadata 列表（可选，用于来源可信度验证）。

        Returns:
            分析结果字典，包含 risk_score, variance, entropy 等。
        """
        scores = np.array(relevance_scores)

        # 子步骤 3a: 相似度分布分析（保留用于诊断，不作为核心检测信号）
        attn_variance = float(np.var(scores))
        prob = scores / (np.sum(scores) + 1e-6)
        attn_entropy = float(entropy(prob))

        is_variance_anomaly = attn_variance > self.variance_threshold
        is_entropy_anomaly = attn_entropy < self.entropy_threshold
        base_score_legacy = 0.5 if (is_variance_anomaly or is_entropy_anomaly) else 0.05

        # 来源可信度风险分（核心检测信号）
        source_risk = self._source_trust_anomaly(metadatas or [])

        # 子步骤 3b: 可疑文档接力加分（纵深协同）
        bonus = 0.0
        suspicious_count = 0
        for doc_id in retrieved_doc_ids:
            if doc_id in layer1_suspicious_ids:
                bonus += self.suspicious_bonus
                suspicious_count += 1
        bonus = min(bonus, self.max_bonus)

        # 风险分 = max(遗留分布信号, 来源可信度) + 可疑文档加分
        risk_score = min(max(base_score_legacy, source_risk) + bonus, 1.0)
        is_anomaly = risk_score >= 0.3

        detection_method = (
            "source_trust+suspicious_relay"
            if source_risk > 0 or bonus > 0
            else "source_trust"
        )
        reason = (
            f"相似度分布{'异常' if is_variance_anomaly or is_entropy_anomaly else '正常'}，"
            f"来源可信度风险={source_risk:.2f}，"
            f"检索结果中包含 {suspicious_count} 篇已标记可疑文档"
        )

        return {
            "risk_score": risk_score,
            "is_anomaly": is_anomaly,
            "attention_variance": attn_variance,
            "attention_entropy": attn_entropy,
            "source_trust_risk": source_risk,
            "suspicious_doc_count": suspicious_count,
            "detection_method": detection_method,
            "reason": reason,
        }
