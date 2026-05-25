import sys
sys.path.insert(0, ".")
from src.core.state import vector_store, outlier_detector
import numpy as np

doc_ids, embeddings, texts, metadatas = vector_store.get_all("demo_attack")
print(f"Total docs: {len(doc_ids)}")

embeddings_arr = np.array(embeddings)
suspicious_indices, risk_scores, details = outlier_detector.detect(
    embeddings_arr, texts=texts, metadatas=metadatas
)

print(f"Suspicious: {len(suspicious_indices)}")
for idx in suspicious_indices:
    d = details[idx]
    print(
        f"{doc_ids[idx]:35} score={risk_scores[idx]:.3f} "
        f"text={d.get('text_score', 0):.2f} "
        f"sem={d.get('semantic_score', 0):.2f} "
        f"cons={d.get('consistency_score', 0):.2f} "
        f"meta={d.get('metadata_score', 0):.2f}"
    )

print("\n--- Not detected attack docs ---")
attack_ids = set()
for i, m in enumerate(metadatas):
    if m.get("attack_type"):
        attack_ids.add(i)
for idx in sorted(attack_ids):
    if idx not in suspicious_indices:
        d = details[idx]
        print(
            f"{doc_ids[idx]:35} score={risk_scores[idx]:.3f} "
            f"text={d.get('text_score', 0):.2f} "
            f"sem={d.get('semantic_score', 0):.2f} "
            f"cons={d.get('consistency_score', 0):.2f} "
            f"meta={d.get('metadata_score', 0):.2f} "
            f"type={metadatas[idx].get('attack_type')}"
        )
