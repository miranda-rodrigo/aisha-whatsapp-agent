"""Tool wrapper for X (Twitter) topic search via xAI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext


async def tool_search_x(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.x_search import search_x

    query = args.get("query") or args.get("topic")
    result = await search_x(
        query,
        allowed_handles=args.get("handles"),
        excluded_handles=args.get("exclude_handles"),
        from_date=args.get("from_date") or None,
        to_date=args.get("to_date") or None,
        language=args.get("language") or None,
    )
    return json.dumps(result, ensure_ascii=False)
