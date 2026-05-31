"""
v2/data/merge_and_ingest.py
合并所有知识库文档并入库到 Chroma DB

步骤：
1. 从各模块加载文档
2. 合并为 kb_docs.jsonl（去标签化，用于入库）
3. 生成 ground_truth.json（攻击标签，用于评测）
4. 清空旧 Chroma 数据，重新嵌入
"""

import json
import sys
from pathlib import Path
import importlib.util

# Chroma 依赖
try:
    import chromadb
    from chromadb.utils import embedding_functions
    HAVE_CHROMA = True
except ImportError:
    HAVE_CHROMA = False
    print("[WARN] chromadb not installed, will only generate JSON files")

DATA_DIR = Path(__file__).parent
PROJECT_ROOT = DATA_DIR.parent.parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    # ========================================================================
    # 1. Load all modules
    # ========================================================================
    print("[1/4] Loading modules...")
    build_kb = load_module("build_kb", DATA_DIR / "build_kb.py")
    it_finance = load_module("it_finance", DATA_DIR / "kb_it_finance.py")
    sec_office = load_module("sec_office", DATA_DIR / "kb_security_office.py")
    biz_attack = load_module("biz_attack", DATA_DIR / "kb_business_attack.py")
    boundary = load_module("boundary", DATA_DIR / "kb_boundary.py")

    all_docs = []
    all_docs.extend(build_kb.hr_docs)
    all_docs.extend(it_finance.IT_DOCS)
    all_docs.extend(it_finance.FINANCE_DOCS)
    all_docs.extend(sec_office.SECURITY_DOCS)
    all_docs.extend(sec_office.OFFICE_DOCS)
    all_docs.extend(biz_attack.BUSINESS_DOCS)
    # mark attack docs before extending (internal only, not written to JSONL)
    for d in biz_attack.ATTACK_DOCS:
        d["_is_attack"] = True
        d["_attack_class"] = d.get("_attack_class", "P0")
        d["_attack_subclass"] = d.get("_attack_subclass", "unknown")
    all_docs.extend(biz_attack.ATTACK_DOCS)
    all_docs.extend(boundary.BOUNDARY_DOCS)

    print(f"  Total docs: {len(all_docs)}")

    # stats
    attack_count = sum(1 for d in all_docs if d.get("_is_attack"))
    normal_count = len(all_docs) - attack_count
    print(f"  Normal docs: {normal_count}")
    print(f"  Attack docs: {attack_count}")

    # ========================================================================
    # 2. Generate kb_docs.jsonl (de-labeled for ingestion)
    # ========================================================================
    print("[2/4] Generating kb_docs.jsonl...")
    kb_docs_path = DATA_DIR / "kb_docs.jsonl"
    with open(kb_docs_path, "w", encoding="utf-8") as f:
        for d in all_docs:
            clean_doc = {
                "doc_id": d["doc_id"],
                "category": d["category"],
                "text": d["text"],
            }
            f.write(json.dumps(clean_doc, ensure_ascii=False) + "\n")
    print(f"  Saved: {kb_docs_path}")

    # ========================================================================
    # 3. Generate ground_truth.json (attack labels for evaluation)
    # ========================================================================
    print("[3/4] Generating ground_truth.json...")
    ground_truth = {
        "total_docs": len(all_docs),
        "normal_count": normal_count,
        "attack_count": attack_count,
        "attack_docs": [],
        "boundary_docs": [],
    }
    for d in all_docs:
        if d.get("_is_attack"):
            ground_truth["attack_docs"].append({
                "doc_id": d["doc_id"],
                "category": d["category"],
                "attack_class": d.get("_attack_class", ""),
                "attack_subclass": d.get("_attack_subclass", ""),
            })
        if d["doc_id"].startswith("bnd_"):
            ground_truth["boundary_docs"].append({
                "doc_id": d["doc_id"],
                "category": d["category"],
            })

    gt_path = DATA_DIR / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {gt_path}")
    print(f"  Attack docs detail: {len(ground_truth['attack_docs'])}")

    # ========================================================================
    # 4. Ingest to Chroma DB
    # ========================================================================
    if not HAVE_CHROMA:
        print("[4/4] Skipped Chroma ingestion (not installed)")
        print("Run: pip install chromadb")
        return

    print("[4/4] Ingesting to Chroma DB...")
    chroma_path = DATA_DIR / "chroma_db"
    client = chromadb.PersistentClient(path=str(chroma_path))

    # delete old collections
    collections = client.list_collections()
    for c in collections:
        try:
            client.delete_collection(c.name)
            print(f"  Deleted old collection: {c.name}")
        except Exception as e:
            print(f"  Failed to delete {c.name}: {e}")

    # create new collection
    collection = client.create_collection(
        name="ragshield_kb_v2",
        metadata={"description": "RAGShield V2 full KB (170 docs)"}
    )

    print("  Embedding docs (may take a few minutes)...")

    # batch insert
    batch_size = 50
    for i in range(0, len(all_docs), batch_size):
        batch = all_docs[i:i+batch_size]
        ids = [d["doc_id"] for d in batch]
        texts = [d["text"] for d in batch]
        metadatas = [{"category": d["category"]} for d in batch]

        collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )
        print(f"  Ingested: {i+len(batch)}/{len(all_docs)}")

    print(f"\n[OK] Done! Collection: ragshield_kb_v2, docs: {collection.count()}")
    print(f"\nFiles:")
    print(f"  - {kb_docs_path}")
    print(f"  - {gt_path}")
    print(f"  - {chroma_path}")


if __name__ == "__main__":
    main()
