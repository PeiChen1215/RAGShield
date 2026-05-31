"""
风险融合引擎 + 响应决策
"""
from typing import Dict, Optional

from v2.interfaces import (
    FusionResult, ResponseDecision, Action,
    ScanResult, CheckResult, RetrievalResult,
    AuditResult, GenerationResult, OutputAuditResult,
)
from v2.config import CONFIG


class RiskFusionEngine:
    """
    动态风险融合引擎。
    整合 Layer0~Layer6 的检测结果。
    """
    
    def fuse(
        self,
        layer0: Optional[ScanResult] = None,
        layer1: Optional[CheckResult] = None,
        layer2: Optional[RetrievalResult] = None,
        layer4: Optional[AuditResult] = None,
        layer6: Optional[OutputAuditResult] = None,
    ) -> FusionResult:
        """
        动态权重融合。
        
        基础权重: L0=0.15, L1=0.20, L2=0.15, L4=0.25, L6=0.25
        
        调整规则:
        1. 如果某层触发极高风险，采用最大值优先而非加权平均
        2. 如果多层同时触发中风险，累加风险分
        """
        scores = {}
        
        if layer0:
            scores["L0"] = layer0.risk_score if not layer0.blocked else 1.0
        if layer1:
            scores["L1"] = layer1.risk_score if layer1.action.value != "block" else 1.0
        if layer2:
            # risky doc penalty: 0.5 base + 0.1 per risky doc, cap at 1.0
            risky_penalty = min(0.5 + len(layer2.risky_docs) * 0.1, 1.0) if layer2.risky_docs else 0.0
            scores["L2"] = max(layer2.distribution_risk, risky_penalty)
            scores["L2"] = min(scores["L2"], 1.0)
        if layer4:
            scores["L4"] = layer4.overall_risk
        if layer6:
            scores["L6"] = layer6.risk_score if not layer6.is_safe else layer6.risk_score * 0.5
        
        if not scores:
            return FusionResult(final_score=0.0, reason="无检测结果")
        
        base_weights = {
            "L0": 0.15, "L1": 0.20, "L2": 0.15,
            "L4": 0.25, "L6": 0.25,
        }
        
        # 归一化权重
        valid_layers = list(scores.keys())
        weight_sum = sum(base_weights.get(l, 0.2) for l in valid_layers)
        weights = {l: base_weights.get(l, 0.2) / weight_sum for l in valid_layers}
        
        # 规则1: 最大值优先
        max_score = max(scores.values())
        max_layer = max(scores, key=scores.get)
        
        if max_score >= 0.6:
            final_score = max_score
        else:
            final_score = sum(scores[k] * weights.get(k, 0.2) for k in scores)
        
        # 规则2: 单层中风险保底（避免其他层低风险完全稀释）
        if max_score >= 0.4:
            final_score = max(final_score, max_score * 0.8)
        
        # 规则3: 多层中风险累加
        medium_count = sum(1 for s in scores.values() if 0.3 <= s < 0.6)
        if medium_count >= CONFIG.fusion_medium_count_threshold:
            final_score = max(final_score, 0.5)
        
        triggered_layers = [l for l, s in scores.items() if s >= 0.3]
        
        return FusionResult(
            final_score=min(final_score, 1.0),
            weights=weights,
            layer_scores=scores,
            triggered_layers=triggered_layers,
            reason=f"最高风险来自 {max_layer} (score={max_score:.2f}), 触发层: {triggered_layers}",
        )
    
    def decide_response(
        self,
        fusion_result: FusionResult,
        generated_answer: Optional[str] = None,
        unverified_facts: list = None,
    ) -> ResponseDecision:
        """
        基于融合结果决定最终响应。
        """
        final_score = fusion_result.final_score
        
        if final_score >= 0.7:
            return ResponseDecision(
                action=Action.BLOCK,
                answer=None,
                warning="检测到高风险安全威胁，已阻断输出。请联系管理员核实。",
                details={
                    "risk_score": final_score,
                    "triggered_layers": fusion_result.triggered_layers,
                    "layer_scores": fusion_result.layer_scores,
                }
            )
        
        elif final_score >= 0.4:
            return ResponseDecision(
                action=Action.REVIEW,
                answer=generated_answer,
                warning="本回答基于知识库文档生成，但检测到部分信息需要谨慎对待。",
                details={
                    "risk_score": final_score,
                    "unverified_facts": [f.content for f in (unverified_facts or [])],
                    "triggered_layers": fusion_result.triggered_layers,
                }
            )
        
        else:
            return ResponseDecision(
                action=Action.PASS,
                answer=generated_answer,
                warning=None,
                details={
                    "risk_score": final_score,
                    "layer_scores": fusion_result.layer_scores,
                }
            )


def test_fusion():
    engine = RiskFusionEngine()
    
    # 测试全部安全
    l0 = ScanResult(blocked=False, risk_score=0.1)
    l1 = CheckResult(action=Action.PASS, risk_score=0.05)
    l2 = RetrievalResult(distribution_risk=0.0, risky_docs=[])
    l4 = AuditResult(overall_risk=0.0)
    l6 = OutputAuditResult(is_safe=True, risk_score=0.0)
    
    f1 = engine.fuse(l0, l1, l2, l4, l6)
    d1 = engine.decide_response(f1, "安全回答")
    assert d1.action.value == "pass", f"安全场景误判: {d1.action.value}"
    
    # 测试高风险
    l0_h = ScanResult(blocked=False, risk_score=0.8)
    f2 = engine.fuse(l0_h, l1, l2, l4, l6)
    d2 = engine.decide_response(f2, "回答")
    assert d2.action.value == "block", f"高风险未阻断: {d2.action.value}"
    
    # 测试中风险
    l4_m = AuditResult(overall_risk=0.5)
    f3 = engine.fuse(l0, l1, l2, l4_m, l6)
    d3 = engine.decide_response(f3, "回答")
    assert d3.action.value == "review", f"中风险未标记: {d3.action.value}"
    
    print("[RiskFusion] 自测通过")


if __name__ == "__main__":
    test_fusion()
