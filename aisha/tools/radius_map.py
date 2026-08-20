"""Tool wrapper for drawing a radius circle on a real map."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext

log = logging.getLogger(__name__)


async def tool_draw_radius_map(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.radius_map import build_radius_map

    address = (args.get("address") or "").strip()
    result = await build_radius_map(
        phone=ctx.phone,
        address=address or None,
        latitude=args.get("latitude"),
        longitude=args.get("longitude"),
        radius=args.get("radius"),
        unit=args.get("unit"),
    )
    return json.dumps(result, ensure_ascii=False)
