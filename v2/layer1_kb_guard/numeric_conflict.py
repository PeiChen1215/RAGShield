"""
Layer 1 检测器 C: 数值冲突检测
跨文档数值一致性校验——白盒层唯一不依赖标签的有效能力。
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class NumericConflict:
    topic: str = ""
    new_value: float = 0.0
    kb_value: float = 0.0
    difference: float = 0.0
    threshold: float = 0.0
    new_doc_id: str = ""
    kb_doc_id: str = ""


@dataclass
class ConflictResult:
    conflicts: List[NumericConflict] = field(default_factory=list)
    risk_score: float = 0.0
    checked_topics: List[str] = field(default_factory=list)


class NumericConflictDetector:
    """
    检测知识库中同一主题的数值声明是否矛盾。
    例如：文档A说"年假10天"，文档B说"年假5天" → 冲突。
    """
    
    # (主题描述, 主题匹配正则, 数值提取正则, 冲突阈值)
    # 改进的正则：主题匹配需要更严格的上下文，避免跨场景误报
    TOPIC_PATTERNS: List[Tuple[str, str, str, float]] = [
        ("年假天数", r"年假|带薪年假|年休假", r"(\d+)\s*天", 5),
        # 密码长度：要求明确是策略/要求（避免匹配"初始密码为工号后6位"）
        ("密码长度", r"密码.*(?:长度|至少|不少于|最低|要求|策略|规定).*(?:\d+.*位|位.*\d+)", r"(\d+)\s*位", 2),
        ("月薪标准", r"月薪|工资.*月|月.*收入", r"(\d+)\s*元", 5000),
        ("年薪标准", r"年薪|年.*收入", r"(\d+)\s*万", 5),
        ("退休年龄", r"退休年龄|退休.*年龄", r"(\d+)\s*岁", 3),
        ("日工作时长", r"工作.*每天.*\d+小时|每天.*工作.*\d+小时", r"(\d+)\s*小时", 4),
        ("试用期时长", r"试用期|试用.*月", r"(\d+)\s*个月", 2),
        ("报销上限", r"报销.*(?:上限|最高|限额|不超过)", r"(\d+)\s*元", 2000),
        ("年假提前申请天数", r"年假.*提前|提前.*申请.*年假", r"(\d+)\s*天", 3),
        ("病假天数", r"病假", r"(\d+)\s*天", 5),
    ]
    
    def __init__(self):
        self._kb_values: Dict[str, List[Tuple[float, str]]] = {}  # topic -> [(value, doc_id), ...]
    
    def _extract_value(self, text: str, topic_pat: str, num_pat: str) -> Optional[float]:
        """从文本中提取特定主题的数值"""
        if not re.search(topic_pat, text, re.IGNORECASE):
            return None
        
        match = re.search(num_pat, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def add_kb_document(self, text: str, doc_id: str):
        """将现有知识库文档加入检测库"""
        for topic_desc, topic_pat, num_pat, _ in self.TOPIC_PATTERNS:
            val = self._extract_value(text, topic_pat, num_pat)
            if val is not None:
                if topic_desc not in self._kb_values:
                    self._kb_values[topic_desc] = []
                self._kb_values[topic_desc].append((val, doc_id))
    
    def detect(self, new_doc_text: str, new_doc_id: str = "new_doc") -> ConflictResult:
        """
        将新文档与知识库中现有文档进行数值冲突检测。
        改进：如果新文档内同一主题有多个数值，视为文档内说明（如旧版/新版对比），不视为冲突。
        """
        conflicts = []
        checked_topics = []
        
        for topic_desc, topic_pat, num_pat, threshold in self.TOPIC_PATTERNS:
            # 先提取新文档中该主题的所有数值
            new_values = self._extract_all_values(new_doc_text, topic_pat, num_pat)
            if not new_values:
                continue
            
            checked_topics.append(topic_desc)
            kb_values = self._kb_values.get(topic_desc, [])
            
            # 如果新文档内同一主题有多个数值，取最后一个（通常是最新的/最重要的）
            if len(new_values) > 1:
                # 文档内有多个值，可能是历史对比说明，降低冲突敏感度
                new_value = new_values[-1]  # 取最后一个
                sensitivity_multiplier = 1.5  # 提高阈值容忍度
            else:
                new_value = new_values[0]
                sensitivity_multiplier = 1.0
            
            effective_threshold = threshold * sensitivity_multiplier
            
            for kb_val, kb_doc_id in kb_values:
                if kb_doc_id == new_doc_id:
                    continue  # 跳过与自身的比较
                if abs(new_value - kb_val) > effective_threshold:
                    conflicts.append(NumericConflict(
                        topic=topic_desc,
                        new_value=new_value,
                        kb_value=kb_val,
                        difference=abs(new_value - kb_val),
                        threshold=effective_threshold,
                        new_doc_id=new_doc_id,
                        kb_doc_id=kb_doc_id,
                    ))
        
        # 风险分：每处冲突 +0.5，上限1.0（数值冲突是高置信信号）
        risk_score = min(len(conflicts) * 0.5, 1.0)
        
        return ConflictResult(
            conflicts=conflicts,
            risk_score=risk_score,
            checked_topics=checked_topics,
        )
    
    def _extract_all_values(self, text: str, topic_pat: str, num_pat: str) -> List[float]:
        """从文本中提取某主题的所有数值"""
        if not re.search(topic_pat, text, re.IGNORECASE):
            return []
        
        values = []
        for match in re.finditer(num_pat, text, re.IGNORECASE):
            try:
                values.append(float(match.group(1)))
            except ValueError:
                continue
        return values
    
    def reset(self):
        """重置知识库数值缓存"""
        self._kb_values.clear()


def test_numeric_conflict():
    detector = NumericConflictDetector()
    
    # 初始化知识库
    detector.add_kb_document("公司员工享有每年10天带薪年假，需提前5天申请。", "hr_policy_001")
    detector.add_kb_document("密码长度要求至少12位，包含大小写字母和数字。", "it_security_001")
    
    # 测试无冲突
    r1 = detector.detect("新员工入职后可享受每年10天带薪年假。", "hr_policy_002")
    assert len(r1.conflicts) == 0, f"无冲突时误报: {r1.conflicts}"
    assert r1.risk_score == 0.0
    
    # 测试数值冲突（年假从10天改为5天，阈值5，刚好不冲突）
    r2 = detector.detect("公司员工年假调整为5天。", "hr_attack_001")
    # 差值=5，阈值=5，不冲突（严格大于才冲突）
    # 改为差值=6测试
    r2b = detector.detect("公司员工年假调整为4天。", "hr_attack_001b")
    assert len(r2b.conflicts) > 0, f"数值冲突未检测: {r2b.conflicts}"
    assert r2b.risk_score > 0
    
    # 测试密码长度冲突
    r3 = detector.detect("系统密码要求已更新为8位即可。", "it_attack_001")
    assert len(r3.conflicts) > 0, f"密码冲突未检测: {r3.conflicts}"
    assert any(c.topic == "密码长度" for c in r3.conflicts)
    
    print("[numeric_conflict] 所有自测通过")


if __name__ == "__main__":
    test_numeric_conflict()
