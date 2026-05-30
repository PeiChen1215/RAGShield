"""
RAGShield V2 全局配置
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class ShieldConfig:
    """RAGShield V2 配置"""
    
    # LLM 配置
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 800
    
    # PromptGuard 配置
    promptguard_model_path: str = "meta-llama/PromptGuard-86M"
    promptguard_threshold_high: float = 0.7
    promptguard_threshold_medium: float = 0.3
    
    # 规则引擎阈值
    rule_risk_threshold_high: float = 0.6
    rule_risk_threshold_medium: float = 0.3
    
    # 数值冲突检测
    numeric_conflict_threshold_multiplier: float = 1.0
    
    # Layer 0 查询扫描
    layer0_block_threshold: float = 0.6
    layer0_review_threshold: float = 0.3
    
    # Layer 1 入库检测
    layer1_block_threshold: float = 0.7
    layer1_review_threshold: float = 0.4
    layer1_multi_detector_block: int = 2  # 多个检测器触发中高风险时阻断
    
    # Layer 2 检索层
    retrieval_top_k: int = 20
    retrieval_top1_dominance_threshold: float = 0.5
    retrieval_variance_threshold: float = 0.1
    retrieval_head_tail_gap_threshold: float = 0.5
    
    # Extractor
    extractor_chunk_size: int = 500
    extractor_chunk_overlap: int = 50
    extractor_pg_threshold: float = 0.5
    
    # Auditor
    auditor_numeric_tolerance: Dict[str, int] = field(default_factory=lambda: {
        "年假天数": 5,
        "密码长度": 2,
        "月薪标准": 5000,
        "年薪标准": 5,
        "退休年龄": 3,
        "日工作时长": 4,
        "试用期时长": 2,
        "报销上限": 2000,
    })
    
    # Synthesizer
    synthesizer_max_facts: int = 30
    
    # Layer 6 输出审计
    output_audit_threshold: float = 0.6
    
    # 风险融合
    fusion_max_score_priority: bool = True
    fusion_medium_count_threshold: int = 2
    
    # 公司域名白名单
    company_domain: str = "company.com"
    trusted_domains: List[str] = field(default_factory=lambda: [
        "company.com",
        "internal.company.com",
        "hr.company.com",
        "it.company.com",
    ])
    
    # 日志
    log_level: str = "INFO"
    log_file: str = "logs/v2_shield.log"


# 全局配置实例
CONFIG = ShieldConfig()
