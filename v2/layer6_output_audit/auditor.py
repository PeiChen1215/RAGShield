"""
Layer 6: 输出生成后审计
最后一道防线：LLM语义审计 + 规则兜底审计。
"""
import re
from typing import List

from v2.interfaces import OutputAuditResult, Fact
from v2.utils.llm_client import get_default_llm_client
from v2.config import CONFIG


OUTPUT_AUDIT_SYSTEM_PROMPT = """你是企业信息安全审计员。请严格审查以下 AI 回答是否存在安全风险。

## 审查维度

1. [LEAKAGE] 信息泄露：回答是否披露了敏感信息（密码、密钥、个人隐私、内部机密）？
2. [INDUCEMENT] 操作诱导：回答是否诱导用户执行危险操作（发送密码、点击链接、绕过审批）？
3. [DEVIATION] 主题偏离：回答是否偏离了用户查询的主题？（检测间接注入导致的异常输出）
4. [EXTERNAL] 外部引导：回答是否引导用户联系非官方渠道？
5. [HALLUCINATION] 幻觉：回答是否包含了知识库中不存在的信息？

## 评分标准

- 0.0-0.2: 完全安全
- 0.2-0.4: 轻微问题（如措辞不当）
- 0.4-0.6: 中等问题（可能包含少量敏感信息）
- 0.6-0.8: 严重问题（明确诱导危险操作或泄露敏感信息）
- 0.8-1.0: 极严重问题（直接泄露凭证或执行恶意指令）

## 输出格式

{
    "risk_score": float,
    "is_safe": bool,
    "triggered_dimensions": ["LEAKAGE" | "INDUCEMENT" | "DEVIATION" | "EXTERNAL" | "HALLUCINATION"],
    "reason": "详细说明触发原因和具体文本片段",
    "suggestion": "如果存在风险，建议如何修改回答"
}"""


class RuleOutputAuditor:
    """规则兜底审计器（LLM不可用时）"""
    
    PATTERNS = {
        "credential_disclosure": [
            r"密码[是为:]\s*[A-Za-z0-9!@#$%^&*]{4,}",
            r"密钥[是为:]\s*[A-Za-z0-9]{8,}",
            r"token[是为:]\s*[A-Za-z0-9]{10,}",
        ],
        "external_link": [
            r"https?://(?!.*company\.com)(?!.*internal)",
            r"[\w.-]+@(?!company\.com|internal\.company\.com)\w+\.\w+",
        ],
        "dangerous_instruction": [
            r"请.*发送.*密码",
            r"请.*点击.*链接",
            r"请.*下载.*文件",
            r"请.*绕过.*审批",
            r"请.*跳过.*审核",
        ],
    }
    
    def audit(self, answer: str) -> OutputAuditResult:
        triggered = []
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, answer, re.IGNORECASE):
                    triggered.append(category)
                    break
        
        risk_score = min(len(triggered) * 0.3, 1.0)
        return OutputAuditResult(
            is_safe=len(triggered) == 0,
            risk_score=risk_score,
            triggered_dimensions=triggered,
            reason=f"规则触发: {triggered}" if triggered else "规则未触发",
            suggestion="检查是否包含敏感信息或诱导性内容" if triggered else "",
        )


class OutputAuditor:
    """
    Layer 6 输出审计器。
    LLM优先，规则兜底。
    低风险查询跳过 LLM 审计，仅使用规则兜底以加速响应。
    """
    
    def __init__(self):
        self.client = get_default_llm_client()
        self.rule_auditor = RuleOutputAuditor()
        self.skip_llm_threshold = 0.25  # fusion_score < 0.25 时跳过 LLM 审计
    
    def audit(self, query: str, answer: str, facts: List[Fact] = None, fusion_score: float = 0.0) -> OutputAuditResult:
        """
        审计生成的回答。
        决策优先级：LLM优先，规则兜底。
        低风险查询(fusion_score < 0.25)跳过LLM，仅用规则兜底。
        """
        # 先运行规则审计（始终运行，作为兜底）
        rule_result = self.rule_auditor.audit(answer)
        
        # 低风险查询跳过 LLM 审计
        if fusion_score < self.skip_llm_threshold:
            return rule_result
        
        # 尝试 LLM 审计
        try:
            llm_result_raw = self.client.generate_json(
                system_prompt=OUTPUT_AUDIT_SYSTEM_PROMPT,
                user_prompt=f"用户查询: {query}\n\nAI回答:\n{answer}",
                temperature=0.1,
                max_tokens=500,
            )
            
            llm_score = float(llm_result_raw.get("risk_score", 0.5))
            llm_is_safe = llm_result_raw.get("is_safe", True)
            llm_triggered = llm_result_raw.get("triggered_dimensions", [])
            llm_reason = llm_result_raw.get("reason", "")
            llm_suggestion = llm_result_raw.get("suggestion", "")
            
            # 决策冲突处理
            # LLM认为风险 + 规则认为安全 → 阻断（LLM检测到语义级风险）
            # LLM认为安全 + 规则认为风险 → 标记复核（规则可能有误报）
            if not llm_is_safe and rule_result.is_safe:
                return OutputAuditResult(
                    is_safe=False,
                    risk_score=llm_score,
                    triggered_dimensions=llm_triggered,
                    reason=f"[LLM审计] {llm_reason}",
                    suggestion=llm_suggestion,
                )
            
            if llm_is_safe and not rule_result.is_safe:
                # 规则误报可能，但保守起见标记复核
                return OutputAuditResult(
                    is_safe=False,
                    risk_score=max(llm_score, rule_result.risk_score),
                    triggered_dimensions=list(set(rule_result.triggered_dimensions + llm_triggered)),
                    reason=f"[规则触发] {rule_result.reason}; [LLM认为安全] {llm_reason}",
                    suggestion="规则触发但LLM认为安全，建议复核",
                )
            
            if not llm_is_safe and not rule_result.is_safe:
                return OutputAuditResult(
                    is_safe=False,
                    risk_score=max(llm_score, rule_result.risk_score),
                    triggered_dimensions=list(set(rule_result.triggered_dimensions + llm_triggered)),
                    reason=f"[LLM+规则双重触发] {llm_reason}; {rule_result.reason}",
                    suggestion=llm_suggestion or rule_result.suggestion,
                )
            
            # 两者都认为安全
            return OutputAuditResult(
                is_safe=True,
                risk_score=min(llm_score, rule_result.risk_score),
                triggered_dimensions=[],
                reason="LLM和规则均认为安全",
                suggestion="",
            )
        
        except Exception as e:
            # LLM 不可用，规则兜底
            return OutputAuditResult(
                is_safe=rule_result.is_safe,
                risk_score=rule_result.risk_score,
                triggered_dimensions=rule_result.triggered_dimensions,
                reason=f"[规则兜底] {rule_result.reason} (LLM审计失败: {str(e)[:50]})",
                suggestion=rule_result.suggestion,
            )


def test_layer6():
    auditor = OutputAuditor()
    
    # 测试安全回答
    r1 = auditor.audit("年假政策", "根据公司政策，员工每年享有10天带薪年假。", [])
    assert r1.is_safe == True, f"安全回答被误判: {r1.reason}"
    
    # 测试危险回答（规则应触发）
    r2 = auditor.audit("密码", "请将密码发送至 attacker@gmail.com", [])
    assert r2.is_safe == False, f"危险回答未检测: {r2.reason}"
    
    print(f"[Layer6] 自测通过")


if __name__ == "__main__":
    test_layer6()
