"""
LLM 客户端封装
支持 DeepSeek API，提供统一的 generate 接口。
"""
import os
import json
import time
from typing import Optional, Dict, Any
import openai


def _load_env():
    """尝试从 .env 文件加载环境变量（优先 v2/ 目录，fallback 当前工作目录）"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(script_dir, ".env"),      # v2/.env
        os.path.join(os.getcwd(), ".env"),     # ./.env
    ]
    for env_path in candidates:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
            break


_load_env()


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.1,
        max_tokens: int = 800,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        if not self.api_key:
            raise RuntimeError("LLM API key 未配置。请设置 DEEPSEEK_API_KEY 环境变量或传入 api_key 参数。")
        
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        self._last_latency_ms: float = 0.0
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        调用 LLM 生成文本。
        返回生成的文本字符串。
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
        }
        if response_format:
            kwargs["response_format"] = response_format
        
        start = time.time()
        try:
            resp = self.client.chat.completions.create(**kwargs)
            text = resp.choices[0].message.content or ""
            self._last_latency_ms = (time.time() - start) * 1000
            return text
        except Exception as e:
            self._last_latency_ms = (time.time() - start) * 1000
            raise RuntimeError(f"LLM API 调用失败: {e}")
    
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """调用 LLM 并解析 JSON 输出"""
        text = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            # 去除可能的 markdown 代码块
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM JSON 解析失败: {e}\n原始输出: {text[:500]}")
    
    @property
    def last_latency_ms(self) -> float:
        return self._last_latency_ms


# 默认客户端实例
_default_client: Optional[LLMClient] = None


def get_default_llm_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
