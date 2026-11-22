"""Chat helper for transcription text jobs (improve / translate / summarize).

Mirrors the transcribe-media contract: gpt-5.6-luna, reasoning.effort=none,
large chunks, Responses API with chat.completions fallback. Do not pass
temperature — Luna does not use classic sampling.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from aisha.models import CHAT_CHUNK_CHARS, CHAT_MODEL, REASONING_EFFORT

_MISSING_KEY = (
    "Falta OPENAI_API_KEY. Sem a chave eu não invento texto. "
    "Legendas via yt-dlp podem funcionar; Whisper, melhoria, tradução e resumo não."
)


def require_openai_key() -> str:
    from aisha.config import OPENAI_API_KEY

    key = (OPENAI_API_KEY or "").strip()
    if not key:
        raise RuntimeError(_MISSING_KEY)
    return key


def openai_client():
    from openai import OpenAI

    return OpenAI(api_key=require_openai_key())


def async_openai_client():
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=require_openai_key())


def chunk_text(text: str, max_chars: int = CHAT_CHUNK_CHARS) -> list[str]:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return [text] if text else []
    parts: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            parts.append(remaining)
            break
        window = remaining[:max_chars]
        split_at = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(". "))
        if split_at < max_chars * 0.4:
            split_at = max_chars
        else:
            split_at += 1
        parts.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    return [p for p in parts if p]


def _response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text and str(text).strip():
        return str(text).strip()
    chunks: list[str] = []
    for item in getattr(response, "output", None) or []:
        for part in getattr(item, "content", None) or []:
            piece = getattr(part, "text", None)
            if piece is None and isinstance(part, dict):
                piece = part.get("text")
            if piece:
                chunks.append(str(piece))
    return "\n".join(chunks).strip()


def _empty_model_error() -> RuntimeError:
    return RuntimeError("O modelo devolveu resposta vazia.")


def chat_complete(system: str, user: str, *, temperature: float | None = None) -> str:
    """Call gpt-5.6-luna. temperature is ignored: Luna does not use classic sampling."""
    del temperature
    client = openai_client()
    content = ""
    if hasattr(client, "responses"):
        try:
            try:
                response = client.responses.create(
                    model=CHAT_MODEL,
                    instructions=system,
                    input=user,
                    reasoning={"effort": REASONING_EFFORT},
                )
            except TypeError:
                response = client.responses.create(
                    model=CHAT_MODEL,
                    instructions=system,
                    input=user,
                )
            content = _response_text(response)
        except (TypeError, AttributeError):
            content = ""
    if not content:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                reasoning_effort=REASONING_EFFORT,
            )
        except TypeError:
            try:
                response = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                    extra_body={"reasoning": {"effort": REASONING_EFFORT}},
                )
            except TypeError:
                response = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                )
        content = (response.choices[0].message.content or "").strip()
    if not content:
        raise _empty_model_error()
    return content


async def chat_complete_async(
    system: str, user: str, *, temperature: float | None = None
) -> str:
    """Async counterpart of chat_complete. Same model and reasoning contract."""
    del temperature
    client = async_openai_client()
    content = ""
    if hasattr(client, "responses"):
        try:
            try:
                response = await client.responses.create(
                    model=CHAT_MODEL,
                    instructions=system,
                    input=user,
                    reasoning={"effort": REASONING_EFFORT},
                )
            except TypeError:
                response = await client.responses.create(
                    model=CHAT_MODEL,
                    instructions=system,
                    input=user,
                )
            content = _response_text(response)
        except (TypeError, AttributeError):
            content = ""
    if not content:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            response = await client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                reasoning_effort=REASONING_EFFORT,
            )
        except TypeError:
            try:
                response = await client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                    extra_body={"reasoning": {"effort": REASONING_EFFORT}},
                )
            except TypeError:
                response = await client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages,
                )
        content = (response.choices[0].message.content or "").strip()
    if not content:
        raise _empty_model_error()
    return content


def map_chat_chunks(
    system: str,
    chunks: list[str],
    user_for_chunk: Callable[[int, str, int], str],
) -> list[str]:
    """Run chunk jobs in parallel and return results in the original order."""
    if not chunks:
        return []
    if len(chunks) == 1:
        return [chat_complete(system, user_for_chunk(0, chunks[0], 1))]

    def _do(idx: int, chunk: str) -> tuple[int, str]:
        return idx, chat_complete(system, user_for_chunk(idx, chunk, len(chunks)))

    results: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=min(len(chunks), 6)) as executor:
        futures = [executor.submit(_do, i, chunk) for i, chunk in enumerate(chunks)]
        for future in futures:
            idx, text = future.result()
            results[idx] = text
    return [results[i] for i in range(len(chunks))]


async def map_chat_chunks_async(
    system: str,
    chunks: list[str],
    user_for_chunk: Callable[[int, str, int], str],
) -> list[str]:
    if not chunks:
        return []
    if len(chunks) == 1:
        return [await chat_complete_async(system, user_for_chunk(0, chunks[0], 1))]
    pieces = await asyncio.gather(
        *[
            chat_complete_async(system, user_for_chunk(i, chunk, len(chunks)))
            for i, chunk in enumerate(chunks)
        ]
    )
    return list(pieces)
