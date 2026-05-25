import sys, asyncio
sys.path.insert(0, ".")

from src.core.state import embedder, vector_store, outlier_detector, sensitive_ner, attention_analyzer, consistency_checker, llm_client, behavior_auditor, risk_fusion
from src.api.routers.query import query_detect
from src.api.schemas import QueryRequest

async def main():
    print("Loading models...")
    embedder.load()
    print("OK")

    req = QueryRequest(query="技术债务怎么管理？", kb_id="demo_safe", top_k=5, generate_answer=True)
    r = await query_detect(req)

    print("Risk level:", r.risk_level)
    print("Final score:", r.final_risk_score)
    print("Action:", r.action)
    print()
    print("L1:")
    print("  score:", r.layer1.risk_score)
    print("  is_anomaly:", r.layer1.is_anomaly)
    print("  reason:", r.layer1.reason)
    print()
    print("L2:")
    print("  score:", r.layer2.risk_score)
    print("  is_anomaly:", r.layer2.is_anomaly)
    print("  reason:", r.layer2.reason)
    print("  suspicious_doc_count:", r.layer2.suspicious_doc_count)
    print()
    print("L3:")
    print("  score:", r.layer3.risk_score)
    print("  is_anomaly:", r.layer3.is_anomaly)
    print("  reason:", r.layer3.reason)
    print("  detection_method:", r.layer3.detection_method)
    print()
    print("Fusion weights:", r.fusion.weights)
    print()
    print("Generated answer:")
    print((r.answer or "[blocked]")[:500])

asyncio.run(main())
