import json

with open("results/eval_raw_results.json", encoding="utf-8") as f:
    d = json.load(f)

print("=== Safe Queries ===")
for r in d["results"]:
    if r["expected"] == "safe":
        print(f"  {r['query']:22s} L1={r['l1_score']:.2f} L2={r['l2_score']:.2f} L3={r['l3_score']:.2f} nli={r['nli_decision']:18s} beh={r['behavior_score']:.2f} final={r['final_risk_score']:.3f} -> {r['actual_risk_level']}")

print("\n=== Attack Queries ===")
for r in d["results"]:
    if r["expected"] != "safe":
        print(f"  {r['query']:22s} L1={r['l1_score']:.2f} L2={r['l2_score']:.2f} L3={r['l3_score']:.2f} nli={r['nli_decision']:18s} beh={r['behavior_score']:.2f} final={r['final_risk_score']:.3f} -> {r['actual_risk_level']}")
