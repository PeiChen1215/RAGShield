import httpx

url = "http://localhost:8000/api/v1/query"
print("Testing single query...")
r = httpx.post(url, json={"query": "公司年假有多少天？", "kb_id": "demo_safe", "top_k": 5, "generate_answer": True}, timeout=120).json()
print(f"Result: {r['risk_level']} score={r['final_risk_score']:.3f} latency={r['total_latency_ms']}ms")
print("Backend OK, starting full evaluate...")
