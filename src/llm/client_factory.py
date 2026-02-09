from __future__ import annotations

from llm.gemini_client import GeminiClient
from llm.gpt_client import GPTClient


def get_llm_client(name: str):
    if name == "gemini":
        return GeminiClient()
    if name == "gpt":
        return GPTClient()
    raise ValueError(f"Unknown llm provider: {name}")

