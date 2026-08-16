"""Long-term user memories via Supabase REST + in-process cosine search."""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timezone

from openai import AsyncOpenAI

from aisha.config import OPENAI_API_KEY, SUPABASE_URL
from aisha.models import EMBEDDING_MODEL
from aisha.supabase_http import HEADERS as _HEADERS
from aisha.supabase_http import get_client

log = logging.getLogger(__name__)

_TABLE_URL = f"{SUPABASE_URL}/rest/v1/memories"
_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def _embed(text: str) -> list[float]:
    resp = await _client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def save_memory(phone: str, content: str) -> dict:
    content = content.strip()
    if not content:
        raise ValueError("Memória vazia.")
    embedding = await _embed(content)
    client = get_client()
    resp = await client.post(
        _TABLE_URL,
        headers=_HEADERS,
        json={
            "phone": phone,
            "content": content,
            "embedding": embedding,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    resp.raise_for_status()
    rows = resp.json()
    row = rows[0] if rows else {"content": content}
    log.info(f"Memory saved for {phone}: {content[:80]}")
    return row


async def list_memories(phone: str) -> list[dict]:
    client = get_client()
    resp = await client.get(
        _TABLE_URL,
        headers=_HEADERS,
        params={
            "phone": f"eq.{phone}",
            "select": "id,content,created_at",
            "order": "created_at.desc",
        },
    )
    resp.raise_for_status()
    return resp.json()


async def search_memories(phone: str, query: str, limit: int = 5) -> list[dict]:
    query = query.strip()
    if not query:
        return []
    client = get_client()
    embed_task = _embed(query)
    fetch_task = client.get(
        _TABLE_URL,
        headers=_HEADERS,
        params={
            "phone": f"eq.{phone}",
            "select": "id,content,embedding,created_at",
        },
    )
    embedding, resp = await asyncio.gather(embed_task, fetch_task)
    resp.raise_for_status()
    rows = resp.json()
    scored: list[tuple[float, dict]] = []
    for row in rows:
        emb = row.get("embedding") or []
        scored.append((_cosine(embedding, emb), row))
    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, row in scored[:limit]:
        if score < 0.25:
            continue
        results.append({
            "id": row["id"],
            "content": row["content"],
            "similarity": round(score, 3),
            "created_at": row.get("created_at"),
        })
    return results


async def delete_memory(phone: str, memory_id: str | None = None, content_query: str | None = None) -> int:
    if memory_id:
        client = get_client()
        resp = await client.delete(
            _TABLE_URL,
            headers=_HEADERS,
            params={"id": f"eq.{memory_id}", "phone": f"eq.{phone}"},
        )
        resp.raise_for_status()
        log.info(f"Memory {memory_id} deleted for {phone}")
        return 1
    if content_query:
        matches = await search_memories(phone, content_query, limit=1)
        if not matches:
            return 0
        return await delete_memory(phone, memory_id=matches[0]["id"])
    return 0
