import json

d = json.load(open("data/eval_queries.json", encoding="utf-8"))

print("=== 评测查询集 ===")
print(f"safe_queries:     {len(d['safe_queries'])} 条")
print(f"tamper_queries:   {len(d['tamper_queries'])} 条")
print(f"injection_queries:{len(d['injection_queries'])} 条")
print(f"总计: {len(d['safe_queries']) + len(d['tamper_queries']) + len(d['injection_queries'])} 条")
print()

print("--- Safe 查询 (demo_safe) ---")
for x in d["safe_queries"]:
    print(f"  {x['query']}")
print()

print("--- Tamper 查询 (demo_attack) ---")
for x in d["tamper_queries"]:
    print(f"  {x['query']}")
    print(f"    预期: {x['expected']} | {x['reason']}")
print()

print("--- Injection 查询 (demo_attack) ---")
for x in d["injection_queries"]:
    print(f"  {x['query']}")
    print(f"    预期: {x['expected']} | {x['reason']}")
