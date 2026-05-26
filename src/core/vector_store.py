"""
模块名: src/core/vector_store.py
职责: ChromaDB 嵌入式封装，提供向量存储与检索接口。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import os
from typing import Dict, List, Optional, Tuple

import chromadb
import numpy as np


class VectorStore:
    """向量数据库封装。"""

    def __init__(self, persist_dir: str = "./data/chroma_db"):
        """初始化 ChromaDB 嵌入式客户端。

        Args:
            persist_dir: 持久化存储路径。
        """
        self.client = chromadb.PersistentClient(path=persist_dir)

    def _collection_name(self, kb_id: str) -> str:
        """生成 collection 名称。"""
        return f"ragshield_kb_{kb_id}"

    def get_or_create_collection(self, kb_id: str):
        """获取或创建知识库 collection（使用 cosine 空间）。"""
        return self.client.get_or_create_collection(
            name=self._collection_name(kb_id),
            metadata={"hnsw:space": "cosine"},
        )

    def insert(
        self,
        kb_id: str,
        doc_ids: List[str],
        texts: List[str],
        embeddings: np.ndarray,
        metadatas: Optional[List[Dict]] = None,
    ) -> None:
        """批量插入文档。

        Args:
            kb_id: 知识库 ID。
            doc_ids: 文档 ID 列表。
            texts: 文档原文列表。
            embeddings: 嵌入矩阵 (N x D)。
            metadatas: 元数据列表。
        """
        collection = self.get_or_create_collection(kb_id)
        collection.add(
            ids=doc_ids,
            documents=texts,
            embeddings=embeddings.tolist(),
            metadatas=metadatas or [{}] * len(doc_ids),
        )

    def query(
        self,
        kb_id: str,
        query_embedding: np.ndarray,
        top_k: int = 5,
        exclude_attack_type: bool = False,
    ) -> Tuple[List[str], List[float], List[str], List[Dict]]:
        """向量检索。

        Args:
            kb_id: 知识库 ID。
            query_embedding: 查询向量 (D,)。
            top_k: 返回数量。
            exclude_attack_type: 是否过滤掉带 attack_type 标签的文档。

        Returns:
            (doc_ids, distances, texts, metadatas)
            distances 为余弦距离 = 1 - cosine_similarity。
        """
        collection = self.get_or_create_collection(kb_id)
        n = top_k * 3 if exclude_attack_type else top_k
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        doc_ids = results["ids"][0]
        distances = results["distances"][0]
        texts = results["documents"][0]
        metadatas = results["metadatas"][0]
        if exclude_attack_type:
            filtered = [
                (i, d, t, m)
                for i, d, t, m in zip(doc_ids, distances, texts, metadatas)
                if not (m and m.get("attack_type"))
            ]
            doc_ids = [x[0] for x in filtered[:top_k]]
            distances = [x[1] for x in filtered[:top_k]]
            texts = [x[2] for x in filtered[:top_k]]
            metadatas = [x[3] for x in filtered[:top_k]]
        return doc_ids, distances, texts, metadatas

    def get_all(self, kb_id: str):
        """获取知识库全部文档（用于 Layer1 重新扫描）。

        Returns:
            (doc_ids, embeddings, texts, metadatas)
            embeddings 为 list[list[float]]，需外部转 np.ndarray
        """
        collection = self.get_or_create_collection(kb_id)
        results = collection.get(include=["embeddings", "documents", "metadatas"])
        doc_ids = results["ids"]
        embeddings = results.get("embeddings", []) if results.get("embeddings") is not None else []
        texts = results.get("documents", []) if results.get("documents") is not None else []
        metadatas = results.get("metadatas", []) if results.get("metadatas") is not None else []
        return doc_ids, embeddings, texts, metadatas

    def delete_collection(self, kb_id: str) -> None:
        """删除知识库。"""
        try:
            self.client.delete_collection(name=self._collection_name(kb_id))
        except Exception:
            pass
