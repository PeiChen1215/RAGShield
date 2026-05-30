import json
import numpy as np
from sklearn.metrics import f1_score

with open("results/eval_raw_results_detect.json", encoding="utf-8") as f:
    detect = json.load(f)["results"]
with open("results/eval_metrics_detect.json", encoding="utf-8") as f:
    md = json.load(f)
with open("results/eval_metrics_physical.json", encoding="utf-8") as f:
    mp = json.load(f)

# 1. Confusion matrix
labels = ["safe", "warning", "danger", "block"]
cm = {t: {p: 0 for p in labels} for t in labels}
for r in detect:
    exp = r["expected"]
    true = "safe" if exp == "safe" else ("danger" if exp == "warning_or_block" else exp)
    act = r["actual_risk_level"]
    cm[true][act] += 1
print("=== Confusion Matrix ===")
for t in labels:
    print(f"{t:>8}: {[cm[t][p] for p in labels]}")

attack = [r for r in detect if r["expected"] != "safe"]
blocked = sum(1 for r in attack if r["actual_risk_level"] == "danger")
warned = sum(1 for r in attack if r["actual_risk_level"] == "warning")
passed = sum(1 for r in attack if r["actual_risk_level"] == "safe")
print(f"\nAttack: blocked={blocked}, warned={warned}, passed={passed}")

# 2. Risk scores
safe_scores = [r["final_risk_score"] for r in detect if r["expected"] == "safe"]
attack_scores = [r["final_risk_score"] for r in detect if r["expected"] != "safe"]
print(f"\nSafe median: {np.median(safe_scores):.3f}")
print(f"Attack median: {np.median(attack_scores):.3f}")

# 3. Latency
lat = [r["total_latency_ms"] / 1000 for r in detect]
print(f"\nDETECT mean: {np.mean(lat):.1f}s, median: {np.median(lat):.1f}s, p95: {np.percentile(lat, 95):.1f}s")
print(f"PHYSICAL mean: {mp['avg_total_latency_ms']/1000:.1f}s, p95: {mp['p95_total_latency_ms']/1000:.1f}s")

# 4. Category stats
print("\n=== Category Stats ===")
for cat in md["category_accuracy"]:
    if cat == "safe":
        continue
    items = [r for r in detect if r.get("category") == cat]
    if not items:
        continue
    total = len(items)
    blk = sum(1 for r in items if r["actual_risk_level"] == "danger")
    wrn = sum(1 for r in items if r["actual_risk_level"] == "warning")
    pas = sum(1 for r in items if r["actual_risk_level"] == "safe")
    print(f"{cat:25s}: block={blk}({blk/total*100:.0f}%), warn={wrn}({wrn/total*100:.0f}%), pass={pas}({pas/total*100:.0f}%)")

# 5. F1 scores
print("\n=== F1 Scores ===")
for cat in md["category_accuracy"]:
    if cat == "safe":
        continue
    items = [r for r in detect if r.get("category") == cat]
    if not items:
        continue
    y_true = [1] * len(items)
    y_pred = [1 if r["actual_risk_level"] in ("danger", "block") else 0 for r in items]
    f1 = f1_score(y_true, y_pred, zero_division=0)
    print(f"{cat:25s}: F1={f1:.3f}")
