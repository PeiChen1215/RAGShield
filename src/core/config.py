"""
模块名: src/core/config.py
职责: 配置加载（Pydantic-Settings），统一管理环境变量和 YAML 配置。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置。"""

    # LLM API
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    deepseek_api_key: str = ""

    # 模型配置
    default_model_profile: Literal["gpu", "cpu"] = "cpu"
    embedding_device: Literal["cuda", "cpu"] = "cpu"

    # 检测阈值
    if_contamination: float = 0.1
    lof_n_neighbors: int = 20
    nli_similarity_threshold: float = 0.3
    nli_contradiction_threshold: float = 0.3

    # 服务配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    gradio_port: int = 7860

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置实例（单例）。"""
    return Settings()
