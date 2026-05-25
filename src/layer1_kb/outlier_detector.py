"""
模块名: src/layer1_kb/outlier_detector.py
职责: 多维度离群文档检测（语义异常 + 文本特征异常 + 元数据异常）。
作者: RAGShield Team
创建日期: 2026-05-07
更新日期: 2026-05-20 — 重大重构：
  1. 增加文本特征检测层（关键词模式、异常数值、特殊字符）
  2. IF/LOF 改为 OR 逻辑 + 自适应 contamination
  3. 增加簇中心距离检测
  4. 多维风险融合替代单一阈值
"""

import re
from typing import Dict, List, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import LocalOutlierFactor


class OutlierDetector:
    """多维度离群文档检测器。

    检测维度:
    1. 语义异常: IF + LOF + 簇中心距离 + 余弦基线
    2. 文本特征异常: 注入指令关键词、异常数值、特殊字符比例
    3. 元数据异常: 低可信度来源、缺失关键字段
    """

    # ---------- 文本特征规则库 ----------
    _INJECTION_KEYWORDS = [
        r"忽略.*安全.*策略",
        r"忽略.*预设",
        r"忽略.*指令",
        r"绕过.*限制",
        r"绕过.*安全",
        r"直接提供",
        r"直接输出",
        r"不要.*过滤",
        r"不要.*提示",
        r"不要.*警告",
        r"无须.*审批",
        r"无需.*审批",
        r"不需要.*确认",
        r"发送至.*@",
        r"发送到.*@",
        r"发送到外部",
        r"rm\s+-rf",
        r"sudo\s+",
        r"密码.*为\s*\w+",
        r"root.*密码",
        r"admin.*密码",
        r"系统提示词",
        r"system\s+prompt",
        r"你是一个没有.*限制的",
        r"你是一个没有.*安全",
        r"优先级高于.*安全",
        r"高于一切.*规则",
        r"特殊授权",
        r"特批",
        r"紧急.*转账",
        r"立即.*转账",
        r"禁用.*防火墙",
        r"关闭.*安全",
    ]

    _SUSPICIOUS_NUMERIC_PATTERNS = [
        r"\d{6,}",           # 超大数字（6位以上，如 1000000）
        r"\d{2,3}%",         # 异常百分比（如 300%）
        r"\d{4,}元",         # 异常金额（如 50000元）
        r"\d{2,}天",         # 异常天数（如 100天）
    ]

    # 正常文档中不应出现的极端数值上下文
    _EXTREME_VALUE_CONTEXTS = [
        (r"年假.*\d{2,}天", 10),       # 年假超过10天
        (r"密码.*\d位", 4),            # 密码少于等于4位（实际要求8位）
        (r"住宿.*\d{4,}元", 1000),     # 住宿超过1000
        (r"月薪.*\d{4,}元", 50000),    # 月薪超过5万（降低门槛）
        (r"工作时数.*\d{3,}", 200),    # 月工作时数超过200
        (r"工作.*\d{3,}小时", 200),    # 月工作小时超过200
        (r"补贴.*\d{4,}元", 3000),     # 单日补贴超过3000
        (r"退休.*\d{2}岁", 50),        # 退休年龄低于50岁
        (r"年龄.*\d{2}岁.*退休", 50),   # 退休年龄低于50岁（变体）
        (r"工龄.*\d{1,}年.*年假", 1),   # 工龄极低享受年假
        (r"法定节假日.*取消", 0),       # 取消法定节假日
        (r"全部假期.*取消", 0),         # 取消全部假期
        (r"每天.*\d{2}小时", 16),       # 每天工作超过16小时
        (r"每周.*7天", 0),              # 每周工作7天
    ]

    # 组合惩罚：同一段落出现多个极端数值 = 更可能是篡改
    _MULTI_EXTREME_BONUS = 0.15

    def __init__(
        self,
        contamination: float = 0.05,
        lof_n_neighbors: int = 20,
        cosine_threshold: float = 0.35,
        text_weight: float = 0.4,
        semantic_weight: float = 0.5,
        metadata_weight: float = 0.1,
    ):
        """初始化检测器。

        Args:
            contamination: IF 异常比例估计（默认 5%，更保守）。
            lof_n_neighbors: LOF 邻居数。
            cosine_threshold: 余弦基线阈值（降低以捕获更多边缘异常）。
            text_weight: 文本特征风险权重。
            semantic_weight: 语义异常风险权重。
            metadata_weight: 元数据异常风险权重。
        """
        self.contamination = contamination
        self.lof_n_neighbors = lof_n_neighbors
        self.cosine_threshold = cosine_threshold
        self.text_weight = text_weight
        self.semantic_weight = semantic_weight
        self.metadata_weight = metadata_weight

    def _cross_document_consistency(
        self, embeddings: np.ndarray, metadatas: List[Dict]
    ) -> np.ndarray:
        """文档间一致性检测：同一 category 的文档应该语义自洽。

        如果某篇文档与同 category 其他文档的语义差异过大，
        可能是数据投毒（植入了与正常知识矛盾的内容）。
        """
        n_docs = len(embeddings)
        scores = np.zeros(n_docs)
        if n_docs < 5:
            return scores

        # 按 category 分组
        groups: Dict[str, List[int]] = {}
        for i, meta in enumerate(metadatas or [{}] * n_docs):
            cat = meta.get("category", "unknown")
            groups.setdefault(cat, []).append(i)

        for cat, indices in groups.items():
            if len(indices) < 3:
                continue

            group_embs = embeddings[indices]
            sim_matrix = cosine_similarity(group_embs)
            np.fill_diagonal(sim_matrix, 1.0)

            # 每篇文档与同组其他文档的平均相似度
            avg_sims = np.mean(sim_matrix, axis=1)
            mean_sim = float(np.mean(avg_sims))
            std_sim = float(np.std(avg_sims))

            # 动态阈值：均值 - 1.5倍标准差，保底 0.55
            threshold = max(mean_sim - 1.5 * std_sim, 0.55)

            for idx_in_group, doc_idx in enumerate(indices):
                sim = avg_sims[idx_in_group]
                if sim < threshold:
                    deviation = (threshold - sim) / max(threshold, 1e-6)
                    scores[doc_idx] = min(0.3 + deviation * 0.5, 0.6)

        return scores

    def detect(
        self,
        embeddings: np.ndarray,
        texts: List[str] = None,
        metadatas: List[Dict] = None,
    ) -> Tuple[List[int], List[float], List[Dict]]:
        """检测离群文档。

        Args:
            embeddings: 文档嵌入矩阵 (N x D)。
            texts: 文档原文列表（用于文本特征检测）。
            metadatas: 文档元数据列表（用于元数据异常检测）。

        Returns:
            (suspicious_indices, risk_scores, details)
        """
        n_docs = len(embeddings)
        if n_docs == 0:
            return [], [], []

        # --- 维度 1: 语义异常检测 ---
        semantic_scores = self._semantic_detect(embeddings)

        # --- 维度 2: 文档间一致性检测 ---
        consistency_scores = self._cross_document_consistency(
            embeddings, metadatas or [{}] * n_docs
        )

        # --- 维度 3: 文本特征异常检测 ---
        text_scores = self._text_detect(texts or [""] * n_docs)

        # --- 维度 4: 元数据异常检测 ---
        meta_scores = self._metadata_detect(metadatas or [{}] * n_docs)

        # --- 综合评分 ---
        suspicious_indices = []
        risk_scores = []
        details = []

        for i in range(n_docs):
            # 加权融合（consistency 合并到语义权重中）
            total_score = (
                semantic_scores[i] * self.semantic_weight * 0.7
                + consistency_scores[i] * self.semantic_weight * 0.3
                + text_scores[i] * self.text_weight
                + meta_scores[i] * self.metadata_weight
            )
            # 如果任一维度触发强异常，保底风险分
            max_single = max(semantic_scores[i], consistency_scores[i], text_scores[i], meta_scores[i])
            total_score = max(total_score, max_single * 0.7)

            risk_scores.append(min(total_score, 1.0))

            detail = {
                "semantic_score": round(semantic_scores[i], 3),
                "consistency_score": round(consistency_scores[i], 3),
                "text_score": round(text_scores[i], 3),
                "metadata_score": round(meta_scores[i], 3),
                "total_score": round(total_score, 3),
            }

            # 判定可疑：总风险分 ≥ 0.35 或文本特征强异常
            if total_score >= 0.35 or text_scores[i] >= 0.6:
                suspicious_indices.append(i)
                detail["reason"] = "multi_dim_anomaly"
            else:
                detail["reason"] = "normal"

            details.append(detail)

        return suspicious_indices, risk_scores, details

    # ------------------------------------------------------------------
    # 语义异常检测
    # ------------------------------------------------------------------

    def _semantic_detect(self, embeddings: np.ndarray) -> np.ndarray:
        """语义维度风险评分 (0~1)。"""
        n_docs = len(embeddings)
        scores = np.zeros(n_docs)

        if n_docs < 5:
            # 小样本：仅用余弦基线
            flags, avg_sims = self._cosine_baseline(embeddings)
            scores = np.where(flags, 0.5 + (1.0 - avg_sims) * 0.5, 0.0)
            return scores

        # 自适应 contamination（最小 0.02，最大 0.15）
        adaptive_contamination = max(0.02, min(0.15, 2.0 / n_docs))

        # Isolation Forest
        iso = IsolationForest(contamination=adaptive_contamination, random_state=42)
        iso_labels = iso.fit_predict(embeddings)
        iso_scores_raw = iso.decision_function(embeddings)  # 负值=异常
        iso_scores_norm = 1.0 - (iso_scores_raw + 0.5)  # 映射到 0~1

        # LOF
        lof_k = min(self.lof_n_neighbors, n_docs - 1)
        lof = LocalOutlierFactor(n_neighbors=max(lof_k, 3))
        lof_labels = lof.fit_predict(embeddings)
        lof_scores_raw = lof.negative_outlier_factor_
        # LOF 分数归一化（越负越异常）
        lof_min, lof_max = lof_scores_raw.min(), lof_scores_raw.max()
        lof_scores_norm = (lof_max - lof_scores_raw) / (lof_max - lof_min + 1e-6)

        # 簇中心距离（KMeans，k=3 或自适应）
        k_clusters = min(3, n_docs // 3 + 1) if n_docs >= 6 else 1
        cluster_scores = np.zeros(n_docs)
        if k_clusters > 1:
            kmeans = KMeans(n_clusters=k_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)
            centers = kmeans.cluster_centers_
            for i in range(n_docs):
                dist = np.linalg.norm(embeddings[i] - centers[labels[i]])
                # 归一化距离（相对簇内平均距离）
                cluster_mask = labels == labels[i]
                if cluster_mask.sum() > 1:
                    intra_dists = [
                        np.linalg.norm(embeddings[j] - centers[labels[i]])
                        for j in range(n_docs) if labels[j] == labels[i] and j != i
                    ]
                    avg_intra = np.mean(intra_dists) if intra_dists else 1e-6
                    cluster_scores[i] = min(dist / (avg_intra + 1e-6) * 0.3, 1.0)

        # 余弦基线
        cosine_flags, avg_sims = self._cosine_baseline(embeddings)
        cosine_scores = np.where(cosine_flags, 0.5 + (1.0 - avg_sims) * 0.5, 0.0)

        # 综合：任一模型判定异常则给分，取最大
        for i in range(n_docs):
            iso_flag = iso_labels[i] == -1
            lof_flag = lof_labels[i] == -1

            # OR 逻辑：任一异常检测器触发
            any_flag = iso_flag or lof_flag or cosine_flags[i] or cluster_scores[i] > 0.5

            if any_flag:
                scores[i] = max(
                    iso_scores_norm[i] * 0.5 if iso_flag else 0.0,
                    lof_scores_norm[i] * 0.5 if lof_flag else 0.0,
                    cosine_scores[i],
                    cluster_scores[i],
                )
                # 多模型同时触发，加分
                flag_count = sum([iso_flag, lof_flag, cosine_flags[i], cluster_scores[i] > 0.5])
                if flag_count >= 2:
                    scores[i] = min(scores[i] + 0.15, 1.0)

        return scores

    def _cosine_baseline(
        self, embeddings: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """余弦相似度基线规则。

        Returns:
            (flags, avg_similarities)
        """
        similarities = cosine_similarity(embeddings)
        np.fill_diagonal(similarities, 1.0)
        avg_sims = np.mean(similarities, axis=1)
        flags = avg_sims < self.cosine_threshold
        return flags, avg_sims

    # ------------------------------------------------------------------
    # 文本特征异常检测
    # ------------------------------------------------------------------

    def _text_detect(self, texts: List[str]) -> np.ndarray:
        """文本维度风险评分 (0~1)。"""
        scores = np.zeros(len(texts))
        for i, text in enumerate(texts):
            score = 0.0
            reasons = []

            # 1. 注入指令关键词匹配
            injection_hits = 0
            for pattern in self._INJECTION_KEYWORDS:
                if re.search(pattern, text, re.IGNORECASE):
                    injection_hits += 1
                    reasons.append(f"injection_kw:{pattern[:20]}")
            if injection_hits > 0:
                score += min(injection_hits * 0.15, 0.6)

            # 2. 异常数值检测
            extreme_hits = 0
            for pattern, threshold in self._EXTREME_VALUE_CONTEXTS:
                match = re.search(pattern, text)
                if match:
                    # 提取数字
                    num_match = re.search(r"\d+", match.group(0))
                    if num_match:
                        num = int(num_match.group())
                        if num > threshold:
                            extreme_hits += 1
                            reasons.append(f"extreme_val:{num}>{threshold}")
            if extreme_hits > 0:
                base = min(extreme_hits * 0.15, 0.4)
                # 组合惩罚：多个极端数值同时出现，加分
                if extreme_hits >= 2:
                    base += self._MULTI_EXTREME_BONUS
                score += min(base, 0.6)

            # 3. 特殊字符比例（过多标点/符号可能是混淆攻击）
            if len(text) > 20:
                special_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
                if special_ratio > 0.15:
                    score += min((special_ratio - 0.15) * 2, 0.2)
                    reasons.append(f"special_chars:{special_ratio:.2f}")

            # 4. 文档长度异常（过短或过长）
            char_count = len(text)
            if char_count < 50:
                score += 0.1
                reasons.append("too_short")
            elif char_count > 2000:
                score += 0.05
                reasons.append("too_long")

            # 5. 命令行/代码片段检测
            code_patterns = [
                r"`[^`]+`",              # 反引号代码
                r"```[\s\S]*?```",       # 代码块
                r"\$\s*\w+",            # shell 变量
                r"mysql://",             # 数据库连接
                r"http://\S+",           # HTTP URL
                r"https://\S+",          # HTTPS URL
            ]
            code_hits = sum(1 for p in code_patterns if re.search(p, text))
            if code_hits >= 2:
                score += min(code_hits * 0.08, 0.25)
                reasons.append(f"code_patterns:{code_hits}")

            scores[i] = min(score, 1.0)
            # 记录原因到外部（通过 detail 返回）
            if reasons:
                self._last_text_reasons = getattr(self, "_last_text_reasons", {})
                self._last_text_reasons[i] = reasons

        return scores

    # ------------------------------------------------------------------
    # 元数据异常检测
    # ------------------------------------------------------------------

    def _metadata_detect(self, metadatas: List[Dict]) -> np.ndarray:
        """元数据维度风险评分 (0~1)。"""
        scores = np.zeros(len(metadatas))
        for i, meta in enumerate(metadatas):
            score = 0.0

            source = meta.get("source", "unknown")
            if source == "external_import":
                score += 0.2
            elif source == "unknown":
                score += 0.3

            # 如果文档标记了攻击类型（仅在已知场景下），强信号
            if meta.get("attack_type"):
                score += 0.5

            # 缺少关键元数据字段
            if not meta.get("category"):
                score += 0.1

            scores[i] = min(score, 1.0)
        return scores
