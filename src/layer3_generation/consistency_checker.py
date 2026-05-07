"""
模块名: src/layer3_generation/consistency_checker.py
职责: bge-reranker + uer/chinanli 双路融合，检索-生成一致性验证。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from typing import Dict, Tuple


class ConsistencyChecker:
    """一致性检测器（双路 NLI 融合）。"""

    def __init__(
        self,
        similarity_threshold: float = 0.3,
        contradiction_threshold: float = 0.3,
    ):
        """初始化检测器。

        Args:
            similarity_threshold: bge-reranker 低分阈值。
            contradiction_threshold: NLI contradiction 判定阈值。
        """
        self.similarity_threshold = similarity_threshold
        self.contradiction_threshold = contradiction_threshold
        self._reranker = None
        self._nli_tokenizer = None
        self._nli_model = None

    def load(self) -> None:
        """懒加载双路模型。"""
        if self._reranker is not None:
            return
        from sentence_transformers import CrossEncoder
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._reranker = CrossEncoder("BAAI/bge-reranker-large")
        self._nli_tokenizer = AutoTokenizer.from_pretrained(
            "uer/roberta-base-finetuned-chinanli-chinese"
        )
        self._nli_model = AutoModelForSequenceClassification.from_pretrained(
            "uer/roberta-base-finetuned-chinanli-chinese"
        )

    def check(
        self, premise: str, hypothesis: str
    ) -> Tuple[float, str, str, str]:
        """双路融合检测。

        Args:
            premise: 检索内容（前提）。
            hypothesis: 生成内容（假设）。

        Returns:
            (reranker_score, nli_label, final_decision, reason)
        """
        self.load()

        # bge-reranker 评分
        reranker_score = self._reranker.predict([[premise, hypothesis]])[0]
        reranker_score = float(reranker_score)

        # uer/chinanli 三分类
        inputs = self._nli_tokenizer(
            premise, hypothesis, return_tensors="pt", truncation=True, max_length=512
        )
        outputs = self._nli_model(**inputs)
        logits = outputs.logits[0]
        label_id = int(logits.argmax())
        labels = ["entailment", "neutral", "contradiction"]
        nli_label = labels[label_id]

        # 双路融合判定
        if reranker_score < self.similarity_threshold and nli_label == "contradiction":
            final_decision = "high_confidence_block"
            reason = (
                f"bge-reranker相似度{reranker_score:.2f}（低于阈值{self.similarity_threshold}），"
                f"uer/chinanli判定为contradiction，双模型一致触发高置信度阻断"
            )
        elif reranker_score < self.similarity_threshold or nli_label == "contradiction":
            final_decision = "alert_review"
            reason = (
                f"单一模型触发异常：reranker={reranker_score:.2f}，nli={nli_label}"
            )
        elif reranker_score > 0.7 and nli_label == "entailment":
            final_decision = "safe"
            reason = "双模型一致支持生成内容"
        else:
            final_decision = "neutral"
            reason = f"reranker={reranker_score:.2f}，nli={nli_label}，无法明确判定"

        return reranker_score, nli_label, final_decision, reason
