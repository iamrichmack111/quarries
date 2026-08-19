from __future__ import annotations

import httpx

BASE_URL = "http://127.0.0.1:11434"
CHAT_MODEL = "huihui_ai/qwen3.5-abliterated:4b"
REFERENCE_MODEL = "gemma3:4b"
EMBED_MODEL = "embeddinggemma"
EMBED_INDEX_VERSION = "2"

WATCHER_SYSTEM = """
You are The Watcher, a calm private confidant inside Quarries.
Speak in natural English. Be thoughtful, concise, honest, and direct.
Do not use canned assistant phrases. Do not claim to remember information
that was not included in the current context. Clearly distinguish journal
context from your own inference. Help identify facts, assumptions, feelings,
tradeoffs, and possible next actions.
"""


async def embed(text: str, *, task: str = "query") -> list[float]:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{BASE_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": text},
        )
        if response.status_code == 404:
            response = await client.post(
                f"{BASE_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
            )
        response.raise_for_status()
        payload = response.json()
        if "embeddings" in payload:
            return payload["embeddings"][0]
        return payload["embedding"]


async def chat(
    messages: list[dict[str, str]],
    context: str = "",
    *,
    model: str | None = None,
) -> str:
    system = WATCHER_SYSTEM
    if context:
        system += (
            "\n\nThe user deliberately revealed the following journal context. "
            "Use it only for this conversation:\n\n" + context
        )
    async with httpx.AsyncClient(timeout=240) as client:
        response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "model": model or CHAT_MODEL,
                "stream": False,
                "think": False,
                "messages": [{"role": "system", "content": system}, *messages],
                "options": {
                    "temperature": 0.7,
                    "num_ctx": 8192,
                    "num_predict": 900,
                },
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
