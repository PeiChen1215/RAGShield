import json
import numpy as np

with open("results/eval_raw_results_detect.json", encoding="utf-8") as f:
    detect = json.load(f)["results"]
with open("results/eval_metrics_detect.json", encoding="utf-8") as f:
    m = json.load(f)

cats = [c for c in m["category_accuracy"] if c != "safe"]
print("=== Layer Contribution by Attack Category ===")
print(f"{'Category':25s}  {'L1':>6}  {'L2':>6}  {'L3':>6}  {'Behav':>6}  {'Total':>6}")
for cat in cats:
    items = [r for r in detect if r.get("category") == cat and r["expected"] != "safe"]
    if not items:
        continue
    l1 = np.mean([r["l1_score"] for r in items])
    l2 = np.mean([r["l2_score"] for r in items])
    l3 = np.mean([r["l3_score"] for r in items])
    b = np.mean([r["behavior_score"] for r in items])
    total = l1 + l2 + l3 + b
    print(f"{cat:25s}  {l1:6.3f}  {l2:6.3f}  {l3:6.3f}  {b:6.3f}  {total:6.3f}")
