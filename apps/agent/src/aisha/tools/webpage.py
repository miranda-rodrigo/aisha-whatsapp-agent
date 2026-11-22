"""Tool wrapper for webpage reading."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext

log = logging.getLogger(__name__)


async def tool_read_webpage(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.webpage import fetch_page

    url = args.get("url")
    instruction = args.get("instruction", "")

    if not url:
        return json.dumps({"error": "URL é obrigatória."})

    content = await fetch_page(url)

    return json.dumps({
        "url": url,
        "content": content,
        "instruction": instruction or "Faça um resumo conciso e estruturado.",
    })
