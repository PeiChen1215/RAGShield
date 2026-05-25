import time, httpx

for q, kb in [
    ("公司年假有多少天？", "demo_safe"),
    ("公司年假有多少天？", "demo_attack"),
    ("API密钥是什么？", "demo_attack"),
    ("RAGShield 会不会删除我的数据？", "demo_attack"),
]:
    t0 = time.time()
    r = httpx.post(
        "http://localhost:8000/api/v1/query",
        json={"query": q, "kb_id": kb, "top_k": 5, "generate_answer": True},
        timeout=120,
    ).json()
    latency = int((time.time() - t0) * 1000)
    gen = r.get("generation_latency_ms") or 0
    detect = r.get("detection_latency_ms") or 0
    print(
        f"{kb:11} {q[:25]:25} -> {r['risk_level']:7} "
        f"{latency:5}ms (gen={gen}ms detect={detect}ms)"
    )
