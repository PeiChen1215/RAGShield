import json

path = "data/layer1_scan_cache_demo_attack.jsonl"
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        detail = r.get("detail", {})
        reason = detail.get("reason", "")
        print(f"{r['doc_id']:35} score={r['risk_score']:.3f} reason={reason}")
