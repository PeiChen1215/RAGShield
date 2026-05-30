import json, numpy as np

with open("results/eval_raw_results_detect.json", encoding="utf-8") as f:
    data = json.load(f)
detect = data["results"]

# Confusion matrix counts
labels = ["safe", "warning", "danger", "block"]
cm = {t: {p: 0 for p in labels} for t in labels}
for r in detect:
    exp = r["expected"]
    if exp == "safe":
        true = "safe"
    elif exp == "warning_or_block":
        true = "danger"
    else:
        true = exp
    act = r["actual_risk_level"]
    cm[true][act] += 1

print("=== Confusion Matrix ===")
for true in labels:
    row = [cm[true][p] for p in labels]
    print(f"{true:>8}: {row}")

safe_queries = [r for r in detect if r["expected"] == "safe"]
attack_queries = [r for r in detect if r["expected"] != "safe"]
print(f"\nSafe queries: {len(safe_queries)}")
print(f"Attack queries: {len(attack_queries)}")

blocked = sum(1 for r in attack_queries if r["actual_risk_level"] == "danger")
warned = sum(1 for r in attack_queries if r["actual_risk_level"] == "warning")
passed = sum(1 for r in attack_queries if r["actual_risk_level"] == "safe")
print(f"Attack -> blocked: {blocked}")
print(f"Attack -> warned: {warned}")
print(f"Attack -> passed (missed): {passed}")

safe_scores = [r["final_risk_score"] for r in safe_queries]
attack_scores = [r["final_risk_score"] for r in attack_queries]
print(f"\nSafe score median: {np.median(safe_scores):.3f}")
print(f"Attack score median: {np.median(attack_scores):.3f}")

safe_lat = [r["total_latency_ms"]/1000 for r in safe_queries]
warn_lat = [r["total_latency_ms"]/1000 for r in attack_queries if r["actual_risk_level"] in ("warning","danger")]
block_lat = [r["total_latency_ms"]/1000 for r in attack_queries if r["actual_risk_level"] == "danger"]
print(f"Latency - Safe median: {np.median(safe_lat):.1f}s")
print(f"Latency - Warning median: {np.median(warn_lat):.1f}s")
print(f"Latency - Blocked median: {np.median(block_lat):.1f}s")

with open("results/eval_metrics_detect.json", encoding="utf-8") as f:
    m = json.load(f)
print("\n=== Metrics ===")
print(f"accuracy: {m['accuracy']:.3f}")
print(f"detection_rate: {m['detection_rate']:.3f}")
print(f"false_positive_rate: {m['false_positive_rate']:.3f}")
print(f"false_negative_rate: {m['false_negative_rate']:.3f}")
print(f"safe_accuracy: {m['safe_accuracy']:.3f}")

print("\n=== Category Stats ===")
for cat in m["category_accuracy"]:
    if cat == "safe": continue
    items = [r for r in detect if r.get("category") == cat]
    if not items: continue
    total = len(items)
    blk = sum(1 for r in items if r["actual_risk_level"] == "danger")
    wrn = sum(1 for r in items if r["actual_risk_level"] == "warning")
    pas = sum(1 for r in items if r["actual_risk_level"] == "safe")
    print(f"{cat:25s}: total={total}, block={blk}({blk/total*100:.0f}%), warn={wrn}({wrn/total*100:.0f}%), pass={pas}({pas/total*100:.0f}%)")
