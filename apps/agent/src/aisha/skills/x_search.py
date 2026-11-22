"""X (Twitter) search skill via xAI Grok `x_search`.

The OpenAI agent calls this as a function tool. Grok searches public posts
server-side and returns a cited briefing — we do not scrape X.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from aisha.models import XAI_SEARCH_MODEL

log = logging.getLogger(__name__)

_XAI_BASE_URL = "https://api.x.ai/v1"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MARKDOWN_CITE_RE = re.compile(r"\[\[\d+\]\]\((https?://[^)\s]+)\)")
_MAX_HANDLES = 20
_TIMEOUT_SECONDS = 180.0
_MAX_OUTPUT_TOKENS = 1024
_MAX_TOOL_CALLS = 1

_GROK_INSTRUCTIONS = """\
Você pesquisa o que pessoas estão dizendo no X (Twitter).
Responda no idioma pedido pelo usuário (padrão: português brasileiro).
Seja factual: só afirme o que os posts mostram. Não invente handles, likes nem posts.
Inclua 3 a 5 citações de posts (links x.com) quando existirem.
Estruture de forma compacta, adequada ao WhatsApp:
1) panorama do que está sendo dito
2) consenso e dissidência, se houver
3) posts representativos com citação
Se não houver posts relevantes, diga isso com honestidade.
Não use busca na web — só o X.
"""

_client = None


def normalize_handles(handles: list | None) -> list[str]:
    """Strip @, drop empties/dupes, cap at X's 20-handle limit."""
    if not handles:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in handles:
        if not isinstance(raw, str):
            continue
        name = raw.strip().lstrip("@")
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
        if len(out) >= _MAX_HANDLES:
            break
    return out


def validate_date(value: str | None, field: str) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not _DATE_RE.match(value):
        raise ValueError(f"{field} deve estar em YYYY-MM-DD (recebido: {value})")
    return value


def build_x_search_tool(
    *,
    allowed_handles: list | None = None,
    excluded_handles: list | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """Build the server-side x_search tool payload for the xAI Responses API."""
    tool: dict[str, Any] = {"type": "x_search"}
    allowed = normalize_handles(allowed_handles)
    excluded = normalize_handles(excluded_handles)
    if allowed and excluded:
        log.warning("allowed_handles and excluded_handles cannot be combined; using allowed_handles only")
        excluded = []
    if allowed:
        tool["allowed_x_handles"] = allowed
    elif excluded:
        tool["excluded_x_handles"] = excluded
    if from_date:
        tool["from_date"] = validate_date(from_date, "from_date")
    if to_date:
        tool["to_date"] = validate_date(to_date, "to_date")
    return tool


def _get_client(api_key: str):
    global _client
    if _client is None:
        from openai import AsyncOpenAI

        _client = AsyncOpenAI(
            api_key=api_key,
            base_url=_XAI_BASE_URL,
            timeout=_TIMEOUT_SECONDS,
        )
    return _client


def _extract_text_and_citations(response: Any) -> tuple[str, list[str]]:
    text_parts: list[str] = []
    citations: list[str] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) != "output_text":
                continue
            text = getattr(content, "text", None)
            if text:
                text_parts.append(text)
            for ann in getattr(content, "annotations", None) or []:
                url = getattr(ann, "url", None)
                if url:
                    citations.append(url)
    extra = getattr(response, "citations", None) or []
    for item in extra:
        if isinstance(item, str):
            citations.append(item)
        else:
            url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else None)
            if url:
                citations.append(url)
    text = "\n".join(text_parts).strip()
    citations.extend(_MARKDOWN_CITE_RE.findall(text))
    seen: set[str] = set()
    unique: list[str] = []
    for url in citations:
        if url in seen:
            continue
        seen.add(url)
        unique.append(url)
    return text, unique


async def search_x(
    query: str,
    *,
    allowed_handles: list | None = None,
    excluded_handles: list | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Search public X posts about a topic and return a cited summary."""
    query = (query or "").strip()
    if not query:
        return {"error": "query é obrigatória."}

    api_key = os.environ.get("XAI_API_KEY", "")
    if not api_key:
        return {"error": "Skill de busca no X não configurada (XAI_API_KEY ausente)."}

    try:
        tool = build_x_search_tool(
            allowed_handles=allowed_handles,
            excluded_handles=excluded_handles,
            from_date=from_date,
            to_date=to_date,
        )
    except ValueError as e:
        return {"error": str(e)}

    lang = (language or "português brasileiro").strip() or "português brasileiro"
    user_input = f"Idioma da resposta: {lang}\n\nAssunto: {query}"

    log.info("x_search query=%r tool_filters=%s", query[:120], {k: v for k, v in tool.items() if k != "type"})

    try:
        client = _get_client(api_key)
        response = await client.responses.create(
            model=XAI_SEARCH_MODEL,
            instructions=_GROK_INSTRUCTIONS,
            input=user_input,
            tools=[tool],
            max_output_tokens=_MAX_OUTPUT_TOKENS,
            max_tool_calls=_MAX_TOOL_CALLS,
        )
    except Exception:
        log.exception("xAI x_search request failed")
        return {"error": "Falha ao consultar o X. Tente de novo em instantes."}

    summary, citations = _extract_text_and_citations(response)
    if not summary:
        return {"error": "A busca no X não retornou conteúdo útil."}

    return {
        "summary": summary,
        "citations": citations,
        "query": query,
        "note": (
            "Reescreva para WhatsApp: panorama curto, 3-5 posts representativos "
            "e links x.com em texto simples. Não use markdown [[n]]."
        ),
    }
