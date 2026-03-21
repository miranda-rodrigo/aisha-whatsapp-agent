"""Tool wrapper for video download."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext

log = logging.getLogger(__name__)


async def tool_download_video(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.video_download import download_video

    url = args.get("url")
    if not url:
        return json.dumps({"error": "URL do vídeo é obrigatória."})

    token, filename = await download_video(url)
    link = f"{ctx.base_url}/download/{token}"

    return json.dumps({
        "status": "downloaded",
        "filename": filename,
        "download_link": link,
        "expires_in_minutes": 30,
    })
