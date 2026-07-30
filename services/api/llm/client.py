"""The only place a provider-specific LLM detail is allowed to live.

Provider is swapped by editing LLM_BASE_URL / LLM_API_KEY / LLM_MODEL in
.env — no provider-specific code anywhere else in this codebase.
"""
from __future__ import annotations

import os

from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"]
        )
    return _client


async def complete(messages: list[dict], json_mode: bool = False) -> str:
    response = await get_client().chat.completions.create(
        model=os.environ["LLM_MODEL"],
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"} if json_mode else None,
    )
    return response.choices[0].message.content.strip()
