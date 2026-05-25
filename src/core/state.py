"""
模块名: src/core/state.py
职责: 全局单例实例管理，供 lifespan 预加载和各路由共享。
作者: RAGShield Team
创建日期: 2026-05-10
"""

from src.core.embedder import Embedder
from src.core.vector_store import VectorStore
from src.fusion.risk_fusion import RiskFusion
from src.layer1_kb.outlier_detector import OutlierDetector
from src.layer1_kb.sensitive_ner import SensitiveNER
from src.layer2_retrieval.attention_analyzer import AttentionAnalyzer
from src.layer3_generation.behavior_auditor import BehaviorAuditor
from src.layer3_generation.consistency_checker import ConsistencyChecker
from src.layer3_generation.llm_client import LLMClient

# 全局单例实例（ lifespan 预加载 + 路由共享）
embedder = Embedder()
vector_store = VectorStore()
outlier_detector = OutlierDetector()
sensitive_ner = SensitiveNER()
attention_analyzer = AttentionAnalyzer()
consistency_checker = ConsistencyChecker()
llm_client = LLMClient()
behavior_auditor = BehaviorAuditor()
risk_fusion = RiskFusion()
