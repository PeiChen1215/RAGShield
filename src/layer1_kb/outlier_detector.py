"""
模块名: src/layer1_kb/outlier_detector.py
职责: Isolation Forest + LOF + 余弦基线规则，离群文档检测。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from typing import Dict, List, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import LocalOutlierFactor


class OutlierDetector:
    """离群文档检测器。"""

    def __init__(
        self,
        contamination: float = 0.1,
        lof_n_neighbors: int = 20,
        cosine_threshold: float = 0.4,
    ):
        """初始化检测器。

        Args:
            contamination: IF 异常比例估计。
            lof_n_neighbors: LOF 邻居数。
            cosine_threshold: 余弦基线阈值。
        """
        self.contamination = contamination
        self.lof_n_neighbors = lof_n_neighbors
        self.cosine_threshold = cosine_threshold

    def detect(
        self, embeddings: np.ndarray
    ) -> Tuple[List[int], List[float], List[Dict]]:
        """检测离群文档。

        Args:
            embeddings: 文档嵌入矩阵 (N x D)。

        Returns:
            (suspicious_indices, risk_scores, details)
            - suspicious_indices: 可疑文档索引列表
            - risk_scores: 每个文档的风险分数 (0~1)
            - details: 检测详情字典列表
        """
        n_docs = len(embeddings)
        if n_docs < 5:
            # 文档太少，仅使用余弦基线规则
            return self._cosine_only_detect(embeddings)

        # Step 1: Isolation Forest
        iso = IsolationForest(contamination=self.contamination, random_state=42)
        iso_labels = iso.fit_predict(embeddings)
        iso_scores = iso.decision_function(embeddings)

        # Step 2: LOF
        lof = LocalOutlierFactor(n_neighbors=min(self.lof_n_neighbors, n_docs - 1))
        lof_labels = lof.fit_predict(embeddings)
        lof_scores = lof.negative_outlier_factor_

        # Step 3: 余弦基线
        cosine_flags, avg_sims = self._cosine_baseline(embeddings)

        # Step 4: 综合判定 + 评分计算 (Q12 混合法)
        suspicious_indices = []
        risk_scores = []
        details = []

        for i in range(n_docs):
            is_anomaly = (iso_labels[i] == -1 and lof_labels[i] == -1) or cosine_flags[i]

            if not is_anomaly:
                risk_scores.append(0.0)
                details.append({"reason": "正常"})
                continue

            # 异常程度映射 → 0.5~0.7
            iso_norm = (
                min(abs(iso_scores[i]) / (np.max(np.abs(iso_scores)) + 1e-6), 1.0) * 0.35
            )
            lof_norm = min(lof_scores[i] / (np.max(lof_scores) + 1e-6), 1.0) * 0.35
            base_score = 0.5 + min(iso_norm + lof_norm, 0.2)

            # 余弦基线兜底
            if cosine_flags[i]:
                base_score = max(base_score, 0.6)

            risk_scores.append(min(base_score, 1.0))
            suspicious_indices.append(i)
            details.append(
                {
                    "iso_label": int(iso_labels[i]),
                    "lof_label": int(lof_labels[i]),
                    "cosine_flag": bool(cosine_flags[i]),
                    "avg_similarity": float(avg_sims[i]),
                    "base_score": float(base_score),
                }
            )

        return suspicious_indices, risk_scores, details

    def _cosine_baseline(
        self, embeddings: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """余弦相似度基线规则。

        Returns:
            (flags, avg_similarities)
        """
        similarities = cosine_similarity(embeddings)
        # 排除自身（对角线）
        np.fill_diagonal(similarities, 1.0)
        avg_sims = np.mean(similarities, axis=1)
        flags = avg_sims < self.cosine_threshold
        return flags, avg_sims

    def _cosine_only_detect(
        self, embeddings: np.ndarray
    ) -> Tuple[List[int], List[float], List[Dict]]:
        """小样本场景：仅使用余弦基线。"""
        flags, avg_sims = self._cosine_baseline(embeddings)
        suspicious_indices = [i for i, f in enumerate(flags) if f]
        risk_scores = [0.6 if f else 0.0 for f in flags]
        details = [
            {"cosine_flag": bool(f), "avg_similarity": float(s)}
            for f, s in zip(flags, avg_sims)
        ]
        return suspicious_indices, risk_scores, details
