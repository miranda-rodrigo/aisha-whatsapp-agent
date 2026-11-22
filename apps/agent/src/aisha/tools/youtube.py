"""Tool wrapper for YouTube video analysis."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext

log = logging.getLogger(__name__)


async def tool_analyze_youtube_video(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.youtube import analyze_video, store_pending_transcript

    url = args.get("url")
    instruction = args.get("instruction", "")

    if not url:
        return json.dumps({"error": "URL do YouTube é obrigatória."})

    result = await analyze_video(url, instruction)
    if result.download_token:
        store_pending_transcript(ctx.phone, result)
    payload = {"analysis": result.text}
    if result.download_link:
        payload["download_link"] = result.download_link
        payload["filename"] = result.filename
        payload["is_long_video"] = result.is_long
        payload["note"] = (
            "A transcrição completa já está no arquivo TXT. "
            "Encaminhe o resumo e o link. Não omita o download_link."
        )
    return json.dumps(payload)
