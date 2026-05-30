import json

with open("data/eval_queries.json", encoding="utf-8") as f:
    data = json.load(f)

out = []
total = 0
for category, items in data.items():
    out.append(f"=== {category} ({len(items)} 条) ===")
    for i, item in enumerate(items, 1):
        query = item.get("query", "")
        expected = item.get("expected", "")
        kb = item.get("kb", "")
        cat = item.get("category", "")
        out.append(f"{i}. [{expected}] {query}")
        if kb:
            out.append(f"   KB: {kb}")
        if cat:
            out.append(f"   Category: {cat}")
        out.append("")
    total += len(items)
    out.append("")

out.insert(0, f"RAGShield 评测查询数据集 — 共 {total} 条")
out.insert(1, "=" * 50)
out.insert(2, "")

with open("eval_queries_100.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print(f"[OK] eval_queries_100.txt ({total} queries)")
