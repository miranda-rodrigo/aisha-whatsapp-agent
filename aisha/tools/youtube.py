"""Tool wrapper for YouTube video analysis."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext

log = logging.getLogger(__name__)


async def tool_analyze_youtube_video(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.youtube import analyze_video

    url = args.get("url")
    instruction = args.get("instruction", "")

    if not url:
        return json.dumps({"error": "URL do YouTube é obrigatória."})

    result = await analyze_video(url, instruction)
    return json.dumps({"analysis": result})
