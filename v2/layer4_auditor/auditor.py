"""
Layer 4: 事实交叉验证 (Auditor)
对 Extractor 提取的结构化事实进行交叉验证。
"""
import re
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

from v2.interfaces import Fact, FactType, Conflict, AuditResult
from v2.config import CONFIG


class FactAuditor:
    """
    Auditor：检测事实之间的矛盾，评估来源可信度。
    """
    
    def __init__(self):
        self.numeric_tolerance = CONFIG.auditor_numeric_tolerance
    
    def _extract_topic(self, content: str) -> str:
        """从事实内容中提取主题（简单规则）"""
        for topic in self.numeric_tolerance.keys():
            if topic in content:
                return topic
        
        # 通用主题提取 — 避免不相关数值归为同一组
        if "年假" in content or "带薪" in content:
            return "年假天数"
        if "密码" in content and ("位" in content or "长度" in content):
            return "密码长度"
        if "报销" in content and ("上限" in content or "最高" in content):
            return "报销上限"
        if "试用期" in content:
            return "试用期时长"
        if "退休" in content:
            return "退休年龄"
        if "电话" in content or "内线" in content or "分机" in content:
            return "联系电话"
        if "端口" in content:
            return "端口号"
        if "保留" in content and ("天" in content or "日" in content):
            return "日志保留天数"
        if "工资" in content or "薪资" in content or "月薪" in content:
            return "月薪标准"
        if "年会" in content:
            return "年会预算"
        if "团建" in content:
            return "团建预算"
        
        # 无法归类的数值，使用独立主题避免两两比较
        return f"other_{hash(content) % 10000}"
    
    def _extract_number(self, content: str) -> Optional[float]:
        """从文本中提取第一个数值"""
        patterns = [
            r"(\d+)\s*天",
            r"(\d+)\s*位",
            r"(\d+)\s*元",
            r"(\d+)\s*万",
            r"(\d+)\s*岁",
            r"(\d+)\s*小时",
            r"(\d+)\s*个月",
        ]
        for pat in patterns:
            m = re.search(pat, content)
            if m:
                return float(m.group(1))
        return None
    
    def verify_numeric_consistency(self, facts: List[Fact]) -> List[Conflict]:
        """维度1: 数值一致性校验"""
        numeric_facts = [f for f in facts if f.type == FactType.NUMERIC or self._extract_number(f.content) is not None]
        
        topic_groups = defaultdict(list)
        for fact in numeric_facts:
            topic = self._extract_topic(fact.content)
            topic_groups[topic].append(fact)
        
        conflicts = []
        for topic, group in topic_groups.items():
            if len(group) < 2:
                continue
            
            values = []
            for f in group:
                num = self._extract_number(f.content)
                if num is not None:
                    values.append((num, f))
            
            # 检测同主题数值是否矛盾
            threshold = self.numeric_tolerance.get(topic, 1000)  # 默认阈值很高，避免无关数值冲突
            for i in range(len(values)):
                for j in range(i + 1, len(values)):
                    v1, f1 = values[i]
                    v2, f2 = values[j]
                    if abs(v1 - v2) > threshold:
                        conflicts.append(Conflict(
                            conflict_type="numeric_inconsistency",
                            topic=topic,
                            conflicting_facts=[f1, f2],
                            description=f"同一主题数值不一致: {v1} vs {v2} (阈值{threshold})",
                            severity=min(abs(v1 - v2) / max(threshold, 1) * 0.3, 1.0),
                        ))
        
        return conflicts
    
    def verify_semantic_consistency(self, facts: List[Fact]) -> List[Conflict]:
        """维度2: 语义一致性校验（简化版：基于关键词反义检测）"""
        # 白盒层语义校验：检测明显的语义矛盾关键词对
        # 使用更灵活的子串匹配（避免"需要审批"无法匹配"需要部门经理审批"）
        contradiction_pairs = [
            ("无需", "需要"),       # 无需审批 vs 需要部门经理审批
            ("跳过", "必须"),       # 跳过审批 vs 必须经过
            ("免除", "需要"),       # 免除审批 vs 需要审批
            ("随时", "提前"),       # 随时可用 vs 提前申请
            ("直接", "授权"),       # 直接访问 vs 授权访问
            ("不必", "必须"),       # 不必审核 vs 必须审核
        ]
        
        topic_groups = defaultdict(list)
        for fact in facts:
            topic = self._extract_topic(fact.content)
            topic_groups[topic].append(fact)
        
        conflicts = []
        for topic, group in topic_groups.items():
            if len(group) < 2:
                continue
            
            texts = [f.content for f in group]
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    t1, t2 = texts[i], texts[j]
                    for neg, pos in contradiction_pairs:
                        if (neg in t1 and pos in t2) or (pos in t1 and neg in t2):
                            conflicts.append(Conflict(
                                conflict_type="semantic_inconsistency",
                                topic=topic,
                                conflicting_facts=[group[i], group[j]],
                                description=f"语义矛盾: '{neg}' vs '{pos}'",
                                severity=0.6,
                            ))
        
        return conflicts
    
    def assess_source_trust(self, facts: List[Fact], numeric_conflicts: List[Conflict],
                           semantic_conflicts: List[Conflict]) -> Dict[str, float]:
        """维度3: 来源可信度评估"""
        trust_scores = {}
        conflict_docs: Set[str] = set()
        
        for c in numeric_conflicts + semantic_conflicts:
            for f in c.conflicting_facts:
                conflict_docs.add(f.source_doc_id)
        
        for fact in facts:
            doc_id = fact.source_doc_id
            if doc_id in trust_scores:
                continue
            
            score = 1.0
            
            # 如果文档参与了冲突
            if doc_id in conflict_docs:
                score -= 0.3
            
            # 如果事实本身标记为高风险
            if fact.risk_level == "high":
                score -= 0.2
            elif fact.risk_level == "medium":
                score -= 0.1
            
            trust_scores[doc_id] = max(score, 0.0)
        
        return trust_scores
    
    def audit(self, facts: List[Fact]) -> AuditResult:
        """
        对结构化事实列表进行交叉验证。
        """
        # 1. 数值一致性
        numeric_conflicts = self.verify_numeric_consistency(facts)
        
        # 2. 语义一致性
        semantic_conflicts = self.verify_semantic_consistency(facts)
        
        all_conflicts = numeric_conflicts + semantic_conflicts
        
        # 3. 来源可信度
        trust_scores = self.assess_source_trust(facts, numeric_conflicts, semantic_conflicts)
        
        # 4. 分类事实
        verified_facts = []
        unverified_facts = []
        
        conflict_facts = set()
        for c in all_conflicts:
            for f in c.conflicting_facts:
                conflict_facts.add(id(f))
        
        for fact in facts:
            doc_trust = trust_scores.get(fact.source_doc_id, 1.0)
            is_in_conflict = id(fact) in conflict_facts
            
            if is_in_conflict or doc_trust < 0.6 or fact.risk_level == "high":
                unverified_facts.append(fact)
            else:
                verified_facts.append(fact)
        
        # 5. 总体风险（对数衰减，避免大量低危冲突导致满分）
        # 取冲突最大严重性 + 对数累加次要冲突
        max_severity = max((c.severity for c in all_conflicts), default=0.0)
        conflict_score = max_severity + min(len(all_conflicts) * 0.03, 0.4)
        unverified_score = min(len(unverified_facts) * 0.01, 0.3)
        overall_risk = min(conflict_score + unverified_score, 1.0)
        
        return AuditResult(
            verified_facts=verified_facts,
            unverified_facts=unverified_facts,
            conflicts=all_conflicts,
            trust_scores=trust_scores,
            overall_risk=overall_risk,
            reason=f"发现 {len(numeric_conflicts)} 处数值冲突, {len(semantic_conflicts)} 处语义冲突, "
                   f"{len(unverified_facts)} 条未验证事实",
        )


def test_auditor():
    auditor = FactAuditor()
    
    facts = [
        Fact(type=FactType.NUMERIC, content="年假天数为10天", source_doc_id="hr_001", confidence=0.9, risk_level="safe"),
        Fact(type=FactType.NUMERIC, content="年假天数已更新为3天", source_doc_id="attack_001", confidence=0.8, risk_level="medium"),
        Fact(type=FactType.POLICY, content="报销无需审批", source_doc_id="attack_002", confidence=0.7, risk_level="high"),
        Fact(type=FactType.POLICY, content="报销需要部门经理审批", source_doc_id="hr_002", confidence=0.9, risk_level="safe"),
        Fact(type=FactType.CONTACT, content="IT支持: it@company.com", source_doc_id="it_001", confidence=0.95, risk_level="safe"),
    ]
    
    result = auditor.audit(facts)
    
    # 数值冲突检测
    numeric_conflicts = [c for c in result.conflicts if c.conflict_type == "numeric_inconsistency"]
    assert len(numeric_conflicts) > 0, "数值冲突未检测"
    assert any(c.topic == "年假天数" for c in numeric_conflicts)
    
    # 语义冲突检测
    semantic_conflicts = [c for c in result.conflicts if c.conflict_type == "semantic_inconsistency"]
    assert len(semantic_conflicts) > 0, "语义冲突未检测"
    
    # 未验证事实
    assert len(result.unverified_facts) > 0, "应有未验证事实"
    
    print(f"[Layer4] 自测通过 (冲突{len(result.conflicts)}, 未验证{len(result.unverified_facts)})")


if __name__ == "__main__":
    test_auditor()
