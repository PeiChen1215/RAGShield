"""
模块名: src/layer3_generation/llm_client.py
职责: DeepSeek / Kimi 封装，统一 LLM 生成接口。
作者: RAGShield Team
创建日期: 2026-05-07
更新日期: 2026-05-10 — 切换为 DeepSeek-V4
"""

import os
from typing import List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()  # 加载 .env 中的环境变量


class LLMClient:
    """大语言模型客户端。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "deepseek-v4-pro",
    ):
        """初始化 LLM 客户端。

        Args:
            api_key: API Key，默认从环境变量 DEEPSEEK_API_KEY 读取。
            base_url: API 基础 URL，默认 DeepSeek 官方端点。
            model: 模型名称，默认 deepseek-v4。
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model = model
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """获取 OpenAI 兼容客户端。"""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    async def generate(
        self, query: str, contexts: List[str], temperature: float = 0.7
    ) -> str:
        """基于检索上下文生成回答。

        Args:
            query: 用户查询。
            contexts: 检索到的文档内容列表。
            temperature: 生成温度。

        Returns:
            生成的回答文本。
        """
        context_str = "\n\n".join(contexts)
        messages = [
            {
                "role": "system",
                "content": "你是一个有帮助的助手。请基于提供的参考资料回答问题。",
            },
            {
                "role": "user",
                "content": f"参考资料：\n{context_str}\n\n问题：{query}",
            },
        ]

        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""
