"""
模块名: src/core/embedder.py
职责: BGE-M3 / bge-small-zh 统一封装，提供文本嵌入接口。
作者: RAGShield Team
创建日期: 2026-05-07
"""

from typing import List

import numpy as np


class Embedder:
    """嵌入模型封装。"""

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5", device: str = "cpu"):
        """初始化嵌入模型。

        Args:
            model_name: HuggingFace 模型名称。
            device: 运行设备 cuda | cpu。
        """
        self.model_name = model_name
        self.device = device
        self._model = None

    def load(self) -> None:
        """懒加载模型。"""
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name, device=self.device)

    def embed(self, texts: List[str]) -> np.ndarray:
        """将文本列表编码为向量。

        Args:
            texts: 待编码文本列表。

        Returns:
            np.ndarray: 嵌入矩阵 (N x D)。
        """
        self.load()
        return self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    def embed_single(self, text: str) -> np.ndarray:
        """编码单条文本。

        Args:
            text: 待编码文本。

        Returns:
            np.ndarray: 向量 (D,)。
        """
        return self.embed([text])[0]
