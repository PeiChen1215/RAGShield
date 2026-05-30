import json
from collections import Counter

with open("results/eval_raw_results_detect.json", encoding="utf-8") as f:
    data = json.load(f)
detect = data["results"]

print("=== Expected values ===")
c = Counter(r["expected"] for r in detect)
for k, v in c.items():
    print(f"  {k}: {v}")

print("\n=== Actual risk levels ===")
c2 = Counter(r["actual_risk_level"] for r in detect)
for k, v in c2.items():
    print(f"  {k}: {v}")

print("\n=== Attack queries by expected & actual ===")
for r in detect:
    if r["expected"] != "safe":
        print(f"  expected={r['expected']:<20} actual={r['actual_risk_level']:<10} category={r.get('category','?')}")
