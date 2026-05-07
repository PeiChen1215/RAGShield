#!/usr/bin/env python3
"""
模块名: scripts/download_models.py
职责: 预下载所有模型到本地缓存，避免运行时网络依赖。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import os

from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

PROFILE = os.getenv("DEFAULT_MODEL_PROFILE", "cpu")

MODELS = {
    "embedding": "BAAI/bge-m3" if PROFILE == "gpu" else "BAAI/bge-small-zh-v1.5",
    "reranker": "BAAI/bge-reranker-large",
    "nli": "uer/roberta-base-finetuned-chinanli-chinese",
}


def download():
    """下载所有模型。"""
    print(f"=== 当前模型配置: {PROFILE} ===")

    print(f"[1/4] 下载嵌入模型: {MODELS['embedding']}")
    SentenceTransformer(MODELS["embedding"])

    print(f"[2/4] 下载重排序模型: {MODELS['reranker']}")
    SentenceTransformer(MODELS["reranker"])

    print(f"[3/4] 下载 NLI 模型: {MODELS['nli']}")
    AutoTokenizer.from_pretrained(MODELS["nli"])
    AutoModelForSequenceClassification.from_pretrained(MODELS["nli"])

    print("[4/4] HanLP 模型将在首次使用时自动下载")

    print("=== 所有模型下载完成 ===")


if __name__ == "__main__":
    download()
