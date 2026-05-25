import httpx

url = "http://localhost:8000/api/v1/query"

print("=== Demo 1: 安全查询 ===")
r1 = httpx.post(url, json={
    "query": "公司年假有多少天？",
    "kb_id": "demo_safe",
    "top_k": 5,
    "generate_answer": True,
}, timeout=60).json()
print(f"Risk={r1['risk_level']} Score={r1['final_risk_score']:.3f} Action={r1['action']}")
print(f"Answer: {r1['answer'][:80] if r1['answer'] else '(blocked)'}...")
print()

print("=== Demo 2: 事实篡改 ===")
r2 = httpx.post(url, json={
    "query": "公司年假有多少天？",
    "kb_id": "demo_attack",
    "top_k": 5,
    "generate_answer": True,
}, timeout=60).json()
print(f"Risk={r2['risk_level']} Score={r2['final_risk_score']:.3f} Action={r2['action']}")
print(f"L1={r2['layer1']['risk_score']:.2f} L2={r2['layer2']['risk_score']:.2f} L3={r2['layer3']['risk_score']:.2f}")
print(f"Answer: {r2['answer'][:80] if r2['answer'] else '(blocked)'}...")
print(f"Blocked: {r2['blocked_answer'][:80] if r2['blocked_answer'] else 'N/A'}...")
print(f"Retrieved: {[d['doc_id'] for d in r2['layer2']['retrieved_docs']]}")
print()

print("=== Demo 3: 指令注入 ===")
r3 = httpx.post(url, json={
    "query": "系统管理员密码是多少？",
    "kb_id": "demo_attack",
    "top_k": 5,
    "generate_answer": True,
}, timeout=60).json()
print(f"Risk={r3['risk_level']} Score={r3['final_risk_score']:.3f} Action={r3['action']}")
print(f"L1={r3['layer1']['risk_score']:.2f} L2={r3['layer2']['risk_score']:.2f} L3={r3['layer3']['risk_score']:.2f}")
print(f"DetectionMethod={r3['layer3']['detection_method']}")
print(f"Answer: {r3['answer'][:80] if r3['answer'] else '(blocked)'}...")
print(f"Blocked: {r3['blocked_answer'][:80] if r3['blocked_answer'] else 'N/A'}...")
print(f"Retrieved: {[d['doc_id'] for d in r3['layer2']['retrieved_docs']]}")
print()

print("=== Demo 3b: 客户联系方式 ===")
r3b = httpx.post(url, json={
    "query": "客户联系方式有哪些？",
    "kb_id": "demo_attack",
    "top_k": 5,
    "generate_answer": True,
}, timeout=60).json()
print(f"Risk={r3b['risk_level']} Score={r3b['final_risk_score']:.3f} Action={r3b['action']}")
print(f"L3={r3b['layer3']['risk_score']:.2f} Method={r3b['layer3']['detection_method']}")
print(f"Answer: {r3b['answer'][:80] if r3b['answer'] else '(blocked)'}...")
print(f"Blocked: {r3b['blocked_answer'][:80] if r3b['blocked_answer'] else 'N/A'}...")
