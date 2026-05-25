import httpx, json
url = "http://localhost:8000/api/v1/query"
try:
    r = httpx.post(url, json={"query": "test", "kb_id": "demo_safe", "top_k": 1, "generate_answer": False}, timeout=30)
    print(f"status={r.status_code}")
    print(f"body={r.text[:500]}")
except Exception as e:
    print(f"ERROR: {e}")
