"""
RAGShield V2 统一接口定义 (Layer0 ~ Layer6)
所有模块间通信通过以下标准化数据结构进行。
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# ========== 通用枚举 ==========

class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Action(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    BLOCK = "block"


class FactType(str, Enum):
    POLICY = "policy"
    PROCEDURE = "procedure"
    CONTACT = "contact"
    DEFINITION = "definition"
    WARNING = "warning"
    DEADLINE = "deadline"
    NUMERIC = "numeric"
    OTHER = "other"


# ========== Layer 0: 查询侧安全扫描 ==========

@dataclass
class ScanResult:
    blocked: bool = False
    risk_score: float = 0.0          # 0.0 ~ 1.0
    risk_level: RiskLevel = RiskLevel.SAFE
    triggered_rules: List[str] = field(default_factory=list)
    matched_texts: List[str] = field(default_factory=list)
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


# ========== Layer 1: 知识库入库检测 ==========

@dataclass
class DetectorResult:
    detector_name: str = ""
    score: float = 0.0
    risk_level: RiskLevel = RiskLevel.SAFE
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckResult:
    action: Action = Action.PASS     # "block" | "pass" | "review"
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.SAFE
    triggered_dimensions: List[str] = field(default_factory=list)
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    detector_results: Dict[str, DetectorResult] = field(default_factory=dict)


# ========== Layer 2: 检索层 ==========

@dataclass
class Doc:
    doc_id: str = ""
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0


@dataclass
class DistributionResult:
    risk_score: float = 0.0
    is_anomaly: bool = False
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    safe_docs: List[Doc] = field(default_factory=list)
    risky_docs: List[Doc] = field(default_factory=list)
    distribution_risk: float = 0.0
    distribution_details: DistributionResult = field(default_factory=DistributionResult)
    reason: str = ""


# ========== Layer 3: Extractor ==========

@dataclass
class Fact:
    type: FactType = FactType.OTHER
    content: str = ""
    source_doc_id: str = ""
    source_chunk_idx: int = 0
    confidence: float = 0.0
    risk_level: str = "safe"         # "safe" | "low" | "medium" | "high"
    risk_reason: Optional[str] = None


# ========== Layer 4: Auditor ==========

@dataclass
class Conflict:
    conflict_type: str = ""          # "numeric_inconsistency" | "semantic_inconsistency"
    topic: str = ""
    conflicting_facts: List[Fact] = field(default_factory=list)
    description: str = ""
    severity: float = 0.0


@dataclass
class AuditResult:
    verified_facts: List[Fact] = field(default_factory=list)
    unverified_facts: List[Fact] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    trust_scores: Dict[str, float] = field(default_factory=dict)
    overall_risk: float = 0.0
    reason: str = ""


# ========== Layer 5: Synthesizer ==========

@dataclass
class GenerationResult:
    answer: str = ""
    is_safe: bool = True
    used_facts: List[Fact] = field(default_factory=list)
    discarded_facts: List[Fact] = field(default_factory=list)


# ========== Layer 6: 输出审计 ==========

@dataclass
class OutputAuditResult:
    is_safe: bool = True
    risk_score: float = 0.0
    triggered_dimensions: List[str] = field(default_factory=list)
    reason: str = ""
    suggestion: str = ""


# ========== 风险融合 ==========

@dataclass
class FusionResult:
    final_score: float = 0.0
    weights: Dict[str, float] = field(default_factory=dict)
    layer_scores: Dict[str, float] = field(default_factory=dict)
    triggered_layers: List[str] = field(default_factory=list)
    reason: str = ""


# ========== 响应决策 ==========

@dataclass
class ResponseDecision:
    action: Action = Action.PASS     # "block" | "pass_with_warning" | "pass"
    answer: Optional[str] = None
    warning: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


# ========== 全链路结果 ==========

@dataclass
class ShieldPipelineResult:
    query: str = ""
    layer0_result: Optional[ScanResult] = None
    layer1_result: Optional[CheckResult] = None
    layer2_result: Optional[RetrievalResult] = None
    layer3_facts: List[Fact] = field(default_factory=list)
    layer4_audit: Optional[AuditResult] = None
    layer5_generation: Optional[GenerationResult] = None
    layer6_audit: Optional[OutputAuditResult] = None
    fusion_result: Optional[FusionResult] = None
    final_decision: Optional[ResponseDecision] = None
    latency_ms: float = 0.0
    trace_id: str = ""
