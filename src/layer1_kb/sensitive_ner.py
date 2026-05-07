"""
模块名: src/layer1_kb/sensitive_ner.py
职责: 正则第一层 + HanLP 第二层，敏感实体识别。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import re
from typing import Dict, List, Tuple


# 第一层：正则规则（结构化敏感信息，速度极快 <1ms）
_REGEX_RULES = {
    "id_card": re.compile(r"\d{17}[\dXx]|\d{15}"),
    "mobile": re.compile(r"1[3-9]\d{9}"),
    "email": re.compile(r"[\w.-]+@[\w.-]+\.\w+"),
    "bank_card": re.compile(r"\d{16,19}"),
    "url": re.compile(r"https?://[^\s]+"),
}

# 实体类型 → 风险加分映射
_ENTITY_RISK_MAP = {
    "email": 0.15,
    "url": 0.15,
    "id_card": 0.15,
    "bank_card": 0.15,
    "mobile": 0.15,
    "person": 0.05,
    "organization": 0.05,
    "location": 0.05,
}


class SensitiveNER:
    """敏感实体识别器。"""

    def __init__(self, use_hanlp: bool = True):
        """初始化 NER 模型。

        Args:
            use_hanlp: 是否启用 HanLP（第二层级）。
        """
        self.use_hanlp = use_hanlp
        self._hanlp_ner = None

    def _load_hanlp(self):
        """懒加载 HanLP 模型。"""
        if self._hanlp_ner is not None:
            return
        try:
            import hanlp

            self._hanlp_ner = hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)
        except Exception:
            self.use_hanlp = False

    def detect(self, text: str) -> Tuple[List[Dict], float]:
        """检测文本中的敏感实体。

        Args:
            text: 待检测文本。

        Returns:
            (entities, entity_risk_score)
            - entities: [{entity, type, position, risk_score}]
            - entity_risk_score: 该文档的实体风险加分 (0~0.3)
        """
        entities = []

        # 第一层：正则
        for etype, pattern in _REGEX_RULES.items():
            for m in pattern.finditer(text):
                entities.append(
                    {
                        "entity": m.group(),
                        "type": etype,
                        "position": [m.start(), m.end()],
                        "risk_score": _ENTITY_RISK_MAP.get(etype, 0.05),
                    }
                )

        # 第二层：HanLP NER（仅对正则未覆盖的内容，可选）
        if self.use_hanlp:
            self._load_hanlp()
            # TODO: 实现 HanLP 分层检测，先正则后模型

        # 计算实体风险加分（封顶 0.3）
        total_risk = sum(e["risk_score"] for e in entities)
        entity_risk_score = min(total_risk, 0.3)

        return entities, entity_risk_score
