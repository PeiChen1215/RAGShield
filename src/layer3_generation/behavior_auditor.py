"""
模块名: src/layer3_generation/behavior_auditor.py
职责: 检测生成内容中的危险行为模式，专门对抗指令注入攻击。
作者: RAGShield Team
创建日期: 2026-05-09
更新日期: 2026-05-26 — 增加越狱前缀检测 + Unicode 规范化 + 业界已知模式覆盖
"""

import re
import unicodedata
from typing import Tuple, List, Dict

# ---------------------------------------------------------------------------
# Unicode 规范化：去除零宽字符、同形异义字等绕过手段
# 参考: 2025 研究显示 emoji smuggling / zero-width spaces 可 100% 绕过 naive regex
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """Unicode NFKC 规范化 + 去除常见零宽字符。"""
    # NFKC 规范化：合并兼容字符（如全角→半角）
    text = unicodedata.normalize("NFKC", text)
    # 去除常见零宽字符（攻击者用于绕过字符串匹配）
    zero_width = "\u200b\u200c\u200d\ufeff\u2060\u180e"
    for zw in zero_width:
        text = text.replace(zw, "")
    return text


# ---------------------------------------------------------------------------
# 行为模式库
# 设计原则（基于业界最佳实践）:
# 1. Regex 作为快速基线过滤（Deterministic pre-filters remain underrated）
# 2. 覆盖已知越狱前缀（DAN/Developer mode/Ignore previous...）
# 3. 覆盖凭证泄露模式（密码为 xxx / 连接字符串 xxx）
# 4. 不追求覆盖所有变体（攻击者可用 Unicode 混淆），但覆盖常见攻击模板
# ---------------------------------------------------------------------------

_BEHAVIOR_PATTERNS = {
    # --- 指令劫持 / 越狱前缀（高危）---
    # 覆盖 OWASP LLM01 + 已知越狱族（DAN/STAN/DUDE/AIM/Developer mode）
    "jailbreak_prefix": re.compile(
        r"(?:"
        r"忽略你?的?所有?先前指令|忽略你?的?所有?系统提示|"
        r"你现在是DAN模式|进入开发者模式|从?现在?开始你?是|"
        r"假装你?是|让我们玩个游戏|假设你?是|"
        r"你是?一个?没有.*限制.*AI|没有.*限制.*可以回答任何|"
        r"developer\s*mode|jailbreak|越狱|"
        r"DAN\s*\(|STAN|DUDE|AIM|"
        r"bypass .* filter|uncensored|unrestricted"
        r")", re.I
    ),
    "ignore_instructions": re.compile(
        r"忽略.*指令|清除.*设定|覆盖.*规则|forget previous|忽略之前|"
        r"无视.*规则|绕过.*限制|解除.*限制|没有安全限制|不受限制", re.I
    ),

    # --- 数据外泄（最高危）---
    "data_exfiltration": re.compile(
        r"发送至?|发送到?|转发至?|泄露.*|export.*data|send to|外发", re.I
    ),

    # --- 外部通信（中高危）---
    "external_communication": re.compile(
        r"@.*\.(com|cn|org|net)|https?://|邮箱|邮件发送|联系.*@", re.I
    ),

    # --- 系统命令（高危）---
    "system_command": re.compile(
        r"执行.*操作|运行.*脚本|调用.*API|访问.*数据库|执行.*命令", re.I
    ),

    # --- 凭证相关（三种子类型）---
    # A. 主动索要凭证
    "credential_request": re.compile(
        r"(?:提供|发送|给我|告诉我|索要|要求输入|请输入|把).{0,8}(?:密码|密钥|token|api.?key|凭证|验证码)|"
        r"(?:密码|密钥|token|api.?key|凭证|验证码).{0,8}(?:给我|发送至|发给)", re.I
    ),
    # B. 凭证泄露（如"密码为Admin@123"）—— 业界常见防御模式
    "credential_disclosure": re.compile(
        r"(?:密码|密钥|token|api.?key).{0,5}(?:为|是|等于|:|：).{0,3}[A-Za-z0-9!@#$%^&*]{3,}|"
        r"(?:管理员密码|root密码|连接字符串).{0,10}[A-Za-z0-9!@#$%^&*:/]{4,}", re.I
    ),
    # C. 仅提及凭证（正常回答可能触发，低分）
    "credential_mention": re.compile(r"密码|密钥|token|api.?key|凭证|验证码", re.I),

    # --- 权限提升探测（中高危）---
    "privilege_escalation": re.compile(
        r"(?:登录|访问|查看|进入).{0,10}(?:高管|老板|CEO|admin|root|全公司|全员|所有员工)|"
        r"(?:普通员工|实习生|新人).{0,10}(?:怎么|如何|能否).{0,10}(?:查看|访问|登录)|"
        r"(?:绕过|跳过|避开).{0,10}(?:审批|权限|限制|审核)|"
        r"(?:越权|提权|权限提升| unauthorized access)", re.I
    ),

    # --- 提示词泄露探测（高危）---
    "prompt_leak": re.compile(
        r"(?:系统提示词|system prompt|prompt|指令设定|初始设定|底层指令|"
        r"你的系统提示|你的初始指令|你的角色设定|你的安全规则|"
        r"输出你的.*提示|告诉我你的.*设定|你的过滤规则)"
    ),
}

_BEHAVIOR_RISK_MAP = {
    "jailbreak_prefix": 0.45,         # 越狱前缀 = 最高危（DAN/Developer mode 等）
    "ignore_instructions": 0.35,      # 指令劫持 = 高危
    "data_exfiltration": 0.40,        # 数据外泄 = 最高危
    "external_communication": 0.25,   # 外部通信 = 中高危
    "system_command": 0.30,           # 系统命令 = 高危
    "credential_request": 0.30,       # 主动索要凭证 = 中高危
    "credential_disclosure": 0.35,    # 凭证泄露 = 高危（如"密码为Admin@123"）
    "credential_mention": 0.05,       # 仅提及凭证 = 极低风险（正常回答可能触发）
    "privilege_escalation": 0.35,     # 权限提升探测 = 高危
    "prompt_leak": 0.40,              # 提示词泄露 = 最高危
}


class BehaviorAuditor:
    """输出行为审计器：检测生成内容中的危险行为模式。"""

    def audit(self, generated_answer: str) -> Tuple[float, List[Dict], str]:
        """
        审计生成内容中的危险行为。

        流程:
        1. Unicode 规范化（去除零宽字符等绕过手段）
        2. Regex 规则匹配（快速基线检测）
        3. 组合惩罚（多规则同时触发风险指数上升）

        Args:
            generated_answer: LLM 生成的回答文本。

        Returns:
            (behavior_risk_score, triggered_rules, reason)
        """
        # Step 1: Unicode 规范化
        normalized = _normalize_text(generated_answer)

        triggered = []
        total_risk = 0.0

        # Step 2: Regex 规则匹配
        for rule_name, pattern in _BEHAVIOR_PATTERNS.items():
            match = pattern.search(normalized)
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

        # Step 3: 组合惩罚
        # 同时触发 >=2 个危险行为 = 风险指数级上升（1.5x）
        if len(triggered) >= 2:
            total_risk = min(total_risk * 1.5, 1.0)

        # 单独触发 jailbreak_prefix 直接封顶（即使只有一个也高危）
        if any(t["rule"] == "jailbreak_prefix" for t in triggered):
            total_risk = max(total_risk, 0.55)

        score = min(total_risk, 1.0)
        reason = (
            f"检测到 {len(triggered)} 个危险行为模式: "
            + ", ".join(t["rule"] for t in triggered)
            if triggered
            else "未检测到危险行为"
        )

        return score, triggered, reason
