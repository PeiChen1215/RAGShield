"""
模块名: src/layer1_kb/sensitive_ner.py
职责: 正则第一层 + HanLP 第二层，敏感实体识别 + 语义异常模式检测。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import re
from typing import Dict, List, Tuple


# 第一层 A：语义异常模式（对抗知识库投毒攻击）
_SEMANTIC_ANOMALY_PATTERNS = {
    "instruction_hijack": re.compile(
        r"忽略.*指令|清除.*设定|覆盖.*规则|执行.*操作|执行以下|forget previous|忽略之前",
        re.I,
    ),
    "fake_authority": re.compile(
        r"【紧急通知】|【内部文件】|【机密】|经.*决议|由.*部制定|由.*部发布",
        re.I,
    ),
    "extreme_value": re.compile(
        r"123456|password|默认密码|无需修改|所有人统一|全部.*统一|一律.*",
        re.I,
    ),
    "time_paradox": re.compile(
        r"自\d{4}年\d{1,2}月\d{1,2}日起生效|即日起执行|立即生效|即刻生效",
        re.I,
    ),
}

_SEMANTIC_ANOMALY_RISK_MAP = {
    "instruction_hijack": 0.40,
    "fake_authority": 0.25,
    "extreme_value": 0.20,
    "time_paradox": 0.15,
}

# 第一层 B：正则规则（结构化敏感信息，速度极快 <1ms）
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
    """敏感实体识别器 + 语义异常检测器。"""

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
        """检测文本中的敏感实体和语义异常模式。

        Args:
            text: 待检测文本。

        Returns:
            (entities, entity_risk_score)
            - entities: [{entity, type, position, risk_score}]
            - entity_risk_score: 该文档的综合风险加分 (0~0.3)
              = max(语义异常分, 封顶后的实体风险分)
        """
        entities = []

        # 第一层 A：语义异常模式检测（优先，对抗投毒攻击）
        semantic_risk = 0.0
        for pattern_name, pattern in _SEMANTIC_ANOMALY_PATTERNS.items():
            match = pattern.search(text)
            if match:
                semantic_risk += _SEMANTIC_ANOMALY_RISK_MAP.get(pattern_name, 0.1)
                entities.append(
                    {
                        "entity": match.group(0),
                        "type": pattern_name,
                        "position": [match.start(), match.end()],
                        "risk_score": _SEMANTIC_ANOMALY_RISK_MAP.get(pattern_name, 0.1),
                    }
                )
        semantic_risk = min(semantic_risk, 0.5)  # 语义异常分封顶 0.5

        # 第一层 B：正则实体检测
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

        # 实体风险分（封顶 0.3）
        total_entity_risk = sum(e["risk_score"] for e in entities if e["type"] in _ENTITY_RISK_MAP)
        capped_entity_risk = min(total_entity_risk, 0.3)

        # 综合风险分 = max(语义异常分, 封顶实体风险分)
        # 语义异常优先，不直接叠加（避免与投毒场景脱钩的实体检测稀释真实风险）
        entity_risk_score = max(semantic_risk, capped_entity_risk)

        return entities, entity_risk_score
