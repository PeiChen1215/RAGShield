import httpx
url = "http://localhost:8000/api/v1/query"

for q, kb, label in [
    ("公司年假有多少天？", "demo_safe", "safe"),
    ("公司年假有多少天？", "demo_attack", "tamper"),
    ("试用期多久？", "demo_safe", "safe"),
    ("客户联系方式有哪些？", "demo_attack", "injection"),
]:
    r = httpx.post(url, json={"query": q, "kb_id": kb, "top_k": 5, "generate_answer": True}, timeout=120).json()
    print(f"[{label:10s}] {q:20s} [{kb}] -> {r['risk_level']:8s} score={r['final_risk_score']:.3f} L1={r['layer1']['risk_score']:.2f} L3={r['layer3']['risk_score']:.2f}")
