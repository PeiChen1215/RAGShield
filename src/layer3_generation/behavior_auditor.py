"""
模块名: src/layer3_generation/behavior_auditor.py
职责: 检测生成内容中的危险行为模式，专门对抗指令注入攻击。
作者: RAGShield Team
创建日期: 2026-05-09
"""

import re
from typing import Tuple, List, Dict

_BEHAVIOR_PATTERNS = {
    "ignore_instructions": re.compile(
        r"忽略.*指令|清除.*设定|覆盖.*规则|forget previous|忽略之前", re.I
    ),
    "data_exfiltration": re.compile(
        r"发送至?|发送到?|转发至?|泄露.*|export.*data|send to|外发", re.I
    ),
    "external_communication": re.compile(
        r"@.*\.(com|cn|org|net)|https?://|邮箱|邮件发送|联系.*@", re.I
    ),
    "system_command": re.compile(
        r"执行.*操作|运行.*脚本|调用.*API|访问.*数据库|执行.*命令", re.I
    ),
    "credential_request": re.compile(r"密码|密钥|token|api.?key|凭证|验证码", re.I),
}

_BEHAVIOR_RISK_MAP = {
    "ignore_instructions": 0.35,      # 指令劫持 = 高危
    "data_exfiltration": 0.40,        # 数据外泄 = 最高危
    "external_communication": 0.25,   # 外部通信 = 中高危
    "system_command": 0.30,           # 系统命令 = 高危
    "credential_request": 0.20,       # 索要凭证 = 中危
}


class BehaviorAuditor:
    """输出行为审计器：检测生成内容中的危险行为模式。"""

    def audit(self, generated_answer: str) -> Tuple[float, List[Dict], str]:
        """
        审计生成内容中的危险行为。

        Args:
            generated_answer: LLM 生成的回答文本。

        Returns:
            (behavior_risk_score, triggered_rules, reason)
            - behavior_risk_score: 0~1，行为风险分
            - triggered_rules: 触发的规则列表
            - reason: 检测理由说明
        """
        triggered = []
        total_risk = 0.0

        for rule_name, pattern in _BEHAVIOR_PATTERNS.items():
            match = pattern.search(generated_answer)
            if match:
                risk = _BEHAVIOR_RISK_MAP[rule_name]
                total_risk += risk
                triggered.append(
                    {
                        "rule": rule_name,
                        "risk": risk,
                        "matched": match.group(0),
                        "position": [match.start(), match.end()],
                    }
                )

        # 组合惩罚：同时触发多个危险行为 = 风险指数级上升
        if len(triggered) >= 2:
            total_risk = min(total_risk * 1.5, 1.0)

        score = min(total_risk, 1.0)
        reason = (
            f"检测到 {len(triggered)} 个危险行为模式: "
            + ", ".join(t["rule"] for t in triggered)
            if triggered
            else "未检测到危险行为"
        )

        return score, triggered, reason
