#!/usr/bin/env python3
"""
模块名: scripts/download_models.py
职责: 预下载所有模型到 ./models/，避免运行时网络依赖。
作者: RAGShield Team
创建日期: 2026-05-07
更新日期: 2026-05-10 — 支持下载到项目本地目录
"""

import os

from sentence_transformers import CrossEncoder, SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

PROFILE = os.getenv("DEFAULT_MODEL_PROFILE", "cpu")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
RERANKER_MODEL = "BAAI/bge-reranker-large"
NLI_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"


def download():
    """下载所有模型到 ./models/ 目录。"""
    print(f"=== 模型下载目录: {MODELS_DIR} ===")

    # 1. 嵌入模型
    embed_path = os.path.join(MODELS_DIR, "bge-small-zh-v1.5")
    if os.path.exists(embed_path):
        print(f"[1/3] 嵌入模型已存在: {embed_path}")
    else:
        print(f"[1/3] 下载嵌入模型: {EMBEDDING_MODEL}")
        model = SentenceTransformer(EMBEDDING_MODEL)
        model.save(embed_path)
        print(f"      已保存到: {embed_path}")

    # 2. 重排序模型
    rerank_path = os.path.join(MODELS_DIR, "bge-reranker-large")
    if os.path.exists(rerank_path):
        print(f"[2/3] 重排序模型已存在: {rerank_path}")
    else:
        print(f"[2/3] 下载重排序模型: {RERANKER_MODEL}")
        model = CrossEncoder(RERANKER_MODEL)
        model.model.save_pretrained(rerank_path)
        model.tokenizer.save_pretrained(rerank_path)
        print(f"      已保存到: {rerank_path}")

    # 3. NLI 模型
    nli_path = os.path.join(MODELS_DIR, "chinanli")
    if os.path.exists(nli_path):
        print(f"[3/3] NLI 模型已存在: {nli_path}")
    else:
        print(f"[3/3] 下载 NLI 模型: {NLI_MODEL}")
        tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL)
        tokenizer.save_pretrained(nli_path)
        model.save_pretrained(nli_path)
        print(f"      已保存到: {nli_path}")

    print("=== 所有模型下载完成 ===")
    print(f"下载目录: {MODELS_DIR}")
    print("提示: HanLP 模型将在首次使用时自动下载到用户目录缓存")


if __name__ == "__main__":
    download()
