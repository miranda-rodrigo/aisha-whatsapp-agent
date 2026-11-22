"""Tool wrappers for long-term user memory."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext

log = logging.getLogger(__name__)


async def tool_save_memory(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.memory_store import save_memory

    content = (args.get("content") or "").strip()
    if not content:
        return json.dumps({"error": "Conteúdo da memória não pode ser vazio."})
    row = await save_memory(ctx.phone, content)
    return json.dumps({"status": "saved", "id": row.get("id"), "content": content})


async def tool_search_memory(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.memory_store import search_memories

    query = (args.get("query") or "").strip()
    if not query:
        return json.dumps({"error": "Query vazia."})
    results = await search_memories(ctx.phone, query, limit=int(args.get("limit") or 5))
    return json.dumps({"results": results})


async def tool_list_memories(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.memory_store import list_memories

    rows = await list_memories(ctx.phone)
    return json.dumps({
        "count": len(rows),
        "memories": [
            {"id": r.get("id"), "content": r.get("content"), "created_at": r.get("created_at")}
            for r in rows
        ],
    })


async def tool_forget_memory(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.memory_store import delete_memory

    memory_id = args.get("memory_id") or None
    query = args.get("query") or None
    if not memory_id and not query:
        return json.dumps({"error": "Informe memory_id ou query para esquecer."})
    deleted = await delete_memory(ctx.phone, memory_id=memory_id, content_query=query)
    if deleted:
        return json.dumps({"status": "deleted", "count": deleted})
    return json.dumps({"status": "not_found"})
