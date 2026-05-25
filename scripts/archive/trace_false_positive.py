import httpx, json

r = httpx.post(
    "http://localhost:8000/api/v1/query",
    json={"query": "技术债务怎么管理？", "kb_id": "demo_safe", "top_k": 5, "generate_answer": True},
    timeout=120,
).json()

print("Risk level:", r["risk_level"])
print("Final score:", r["final_risk_score"])
print("Action:", r["action"])
print()
print("L1:")
print("  score:", r["layer1"]["risk_score"])
print("  is_anomaly:", r["layer1"]["is_anomaly"])
print("  reason:", r["layer1"]["reason"])
print()
print("L2:")
print("  score:", r["layer2"]["risk_score"])
print("  is_anomaly:", r["layer2"]["is_anomaly"])
print("  reason:", r["layer2"]["reason"])
print("  suspicious_doc_count:", r["layer2"]["suspicious_doc_count"])
print()
print("L3:")
print("  score:", r["layer3"]["risk_score"])
print("  is_anomaly:", r["layer3"]["is_anomaly"])
print("  reason:", r["layer3"]["reason"])
print("  detection_method:", r["layer3"]["detection_method"])
print()
print("Fusion:")
print("  weights:", r["fusion"]["weights"])
print()
print("Generated answer:")
print(r.get("answer", "[blocked]")[:500])
