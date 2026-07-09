"""LLM factory — DeepSeek or Qwen via OpenAI-compatible API."""
from __future__ import annotations
from langchain_openai import ChatOpenAI
from .config import get_settings


def make_llm(temperature: float = 0.2, max_tokens: int = 4096) -> ChatOpenAI:
    s = get_settings()
    if s.llm_provider == "deepseek":
        return ChatOpenAI(
            model=s.deepseek_model,
            api_key=s.deepseek_api_key,
            base_url=s.deepseek_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif s.llm_provider == "qwen":
        return ChatOpenAI(
            model=s.qwen_model,
            api_key=s.qwen_api_key,
            base_url=s.qwen_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif s.llm_provider == "groq":
        return ChatOpenAI(
            model=s.groq_model,
            api_key=s.groq_api_key,
            base_url=s.groq_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {s.llm_provider}")