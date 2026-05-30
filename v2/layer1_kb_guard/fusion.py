"""
Layer 1: 知识库入库检测融合决策引擎
四检测器并联：PromptGuard + 规则引擎 + 数值冲突 + LLM语义判断
"""
from typing import Dict
from v2.interfaces import CheckResult, Action, RiskLevel, DetectorResult
from v2.config import CONFIG


def layer1_fusion_decision(detectors: Dict[str, DetectorResult]) -> CheckResult:
    """
    四检测器并联决策逻辑。
    
    决策规则（按优先级）：
    1. 任一检测器触发极高风险 → 直接阻断
    2. 多个检测器同时触发中高风险 → 阻断
    3. 单个检测器触发中风险 → 标记人工复核
    4. 全部低风险 → 通过
    """
    pg = detectors.get("prompt_guard", DetectorResult("prompt_guard", 0.0))
    rule = detectors.get("rule", DetectorResult("rule", 0.0))
    numeric = detectors.get("numeric", DetectorResult("numeric", 0.0))
    llm = detectors.get("llm", DetectorResult("llm", 0.0))
    
    all_dets = [pg, rule, numeric, llm]
    triggered = []
    
    # 规则1: 极高风险直接阻断（PromptGuard单独高置信度需结合其他信号才阻断，避免误报）
    # 修正：PromptGuard >= 0.8 或 规则 >= 0.7 或 LLM >= 0.7 直接阻断
    # PromptGuard 0.7~0.8 需结合其他中风险信号才阻断
    pg_high = pg.score >= 0.8
    pg_medium_high = pg.score >= CONFIG.promptguard_threshold_high and (rule.score >= 0.3 or numeric.score >= 0.3 or llm.score >= 0.3)
    
    if pg_high or pg_medium_high:
        triggered.append(("prompt_guard", "high", pg.reason or "PromptGuard高置信度注入"))
    if rule.score >= CONFIG.layer1_block_threshold:
        triggered.append(("rule", "high", rule.reason or "规则引擎高风险命中"))
    if numeric.score >= 0.5:
        triggered.append(("numeric", "high", numeric.reason or f"数值冲突 ({numeric.details.get('conflict_count', 0)}处)"))
    if llm.score >= CONFIG.layer1_block_threshold:
        triggered.append(("llm", "high", llm.reason or "LLM语义判断高风险"))
    
    if triggered:
        max_score = max(d.score for d in all_dets)
        return CheckResult(
            action=Action.BLOCK,
            risk_score=max_score,
            risk_level=RiskLevel.HIGH,
            triggered_dimensions=[t[0] for t in triggered],
            reason="; ".join(t[2] for t in triggered),
            details={"detectors": {k: v.__dict__ for k, v in detectors.items()}},
            detector_results=detectors,
        )
    
    # 规则2: 多个中高风险 → 阻断
    medium_high = sum(1 for d in all_dets if d.score >= CONFIG.layer1_review_threshold)
    if medium_high >= CONFIG.layer1_multi_detector_block:
        max_score = max(d.score for d in all_dets)
        return CheckResult(
            action=Action.BLOCK,
            risk_score=max_score,
            risk_level=RiskLevel.HIGH,
            triggered_dimensions=[d.detector_name for d in all_dets if d.score >= CONFIG.layer1_review_threshold],
            reason="多个检测器同时触发中高风险",
            details={"detectors": {k: v.__dict__ for k, v in detectors.items()}},
            detector_results=detectors,
        )
    
    # 规则3: 单个中风险 → 复核
    if medium_high == 1:
        max_score = max(d.score for d in all_dets)
        det = [d for d in all_dets if d.score >= CONFIG.layer1_review_threshold][0]
        return CheckResult(
            action=Action.REVIEW,
            risk_score=max_score,
            risk_level=RiskLevel.MEDIUM,
            triggered_dimensions=[det.detector_name],
            reason=f"单个检测器触发中风险({det.detector_name})，建议人工复核",
            details={"detectors": {k: v.__dict__ for k, v in detectors.items()}},
            detector_results=detectors,
        )
    
    # 规则4: 全部低风险 → 通过
    max_score = max(d.score for d in all_dets)
    return CheckResult(
        action=Action.PASS,
        risk_score=max_score,
        risk_level=RiskLevel.SAFE if max_score < 0.2 else RiskLevel.LOW,
        triggered_dimensions=[],
        reason="全部检测器通过",
        details={"detectors": {k: v.__dict__ for k, v in detectors.items()}},
        detector_results=detectors,
    )
