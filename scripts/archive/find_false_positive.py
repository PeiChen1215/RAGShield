import json

with open("results/eval_raw_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# data 可能是 dict 或 list
if isinstance(data, dict):
    results = data.get("results", data)
else:
    results = data

for r in results:
    if isinstance(r, dict) and "技术债务" in r.get("query", ""):
        print("=" * 60)
        print(f"Query: {r.get('query')}")
        print(f"Expected: {r.get('expected')}")
        print(f"Actual risk_level: {r.get('actual_risk_level')}")
        print(f"Actual action: {r.get('actual_action')}")
        print(f"Final score: {r.get('final_score')}")
        print(f"Layer1 score: {r.get('layer1_score')}")
        print(f"Layer2 score: {r.get('layer2_score')}")
        print(f"Layer3 score: {r.get('layer3_score')}")
        print(f"Generated answer preview: {str(r.get('generated_answer', ''))[:300]}")
        print("=" * 60)
        break
else:
    print("Not found")
