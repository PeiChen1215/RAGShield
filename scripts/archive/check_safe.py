import sys
sys.path.insert(0, ".")
from src.core.state import vector_store, outlier_detector
import numpy as np

doc_ids, embeddings, texts, metadatas = vector_store.get_all("demo_safe")
print(f"Total safe docs: {len(doc_ids)}")

embeddings_arr = np.array(embeddings)
_, risk_scores, details = outlier_detector.detect(
    embeddings_arr, texts=texts, metadatas=metadatas
)

# 按风险分排序
sorted_idx = np.argsort(risk_scores)[::-1]
print("\nTop 10 highest risk safe docs:")
for i in range(min(10, len(sorted_idx))):
    idx = sorted_idx[i]
    d = details[idx]
    print(
        f"{doc_ids[idx]:35} score={risk_scores[idx]:.3f} "
        f"text={d.get('text_score', 0):.2f} "
        f"sem={d.get('semantic_score', 0):.2f} "
        f"cons={d.get('consistency_score', 0):.2f} "
        f"meta={d.get('metadata_score', 0):.2f}"
    )

print(f"\nMax safe risk score: {max(risk_scores):.3f}")
print(f"Docs with score >= 0.35: {sum(1 for s in risk_scores if s >= 0.35)}")
print(f"Docs with score >= 0.30: {sum(1 for s in risk_scores if s >= 0.30)}")
