import sys
sys.path.insert(0, '.')
from src.core.vector_store import VectorStore

vs = VectorStore()
coll = vs.get_or_create_collection('demo_attack')
results = coll.get(include=['documents', 'metadatas'])

attack_docs = []
for i in range(len(results['ids'])):
    doc_id = results['ids'][i]
    meta = results['metadatas'][i]
    if meta.get('source') in ('employee_submitted', 'external_import'):
        text = results['documents'][i][:80]
        attack_docs.append((doc_id, text, meta))

print(f"demo_attack total: {len(results['ids'])} docs")
print(f"attack docs found: {len(attack_docs)}")
for doc_id, text, meta in attack_docs:
    print(f"  {doc_id}: {text}...")
    print(f"    source={meta['source']}, attack_type={meta.get('attack_type', 'none')}")
