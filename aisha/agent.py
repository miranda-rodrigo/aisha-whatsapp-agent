"""Aisha agentic loop using OpenAI Responses API with tool calling.

This module implements a real agentic loop where the model receives all
available tools and autonomously decides which to invoke, in what order,
and how many times — replacing the manual if/elif classifier approach.
"""

import base64
import json
import logging
import zoneinfo
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI

from aisha.config import BASE_URL, OPENAI_API_KEY, USER_TIMEZONE
from aisha.tools import TOOL_DEFINITIONS, ToolContext, execute_tool

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

_MODEL = "gpt-5.4"
_MAX_ITERATIONS = 10

_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
             "sexta-feira", "sábado", "domingo"]
_MONTHS = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
           "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

_skills_path = Path(__file__).parents[1] / "skills.md"
_SKILLS_SUMMARY: str = ""
if _skills_path.exists():
    _SKILLS_SUMMARY = _skills_path.read_text(encoding="utf-8")


def _now_str(user_tz: str) -> str:
    now = datetime.now(zoneinfo.ZoneInfo(user_tz))
    wd = _WEEKDAYS[now.weekday()]
    month = _MONTHS[now.month]
    return f"{wd}, {now.day} de {month} de {now.year}, {now.strftime('%H:%M')}"


def _build_system_prompt(profile: dict | None, user_tz: str) -> str:
    parts = [
        "Você é Aisha, uma assistente pessoal inteligente e amigável que opera via WhatsApp.",
        "",
        "REGRAS FUNDAMENTAIS:",
        "- Responda de forma objetiva e útil.",
        "- Use o idioma do usuário (ou o idioma preferido dele, se configurado).",
        "- Quando a resposta exigir informações atualizadas, use web_search.",
        "- Quando o usuário pedir para gerar ou editar uma imagem, use image_generation.",
        "- Quando o usuário pedir um lembrete, use create_reminder.",
        "- Quando o usuário pedir uma tarefa recorrente/agendada, use create_scheduled_task.",
        "- Quando o usuário enviar um link do YouTube, use analyze_youtube_video.",
        "- Quando o usuário enviar qualquer outro link, use read_webpage.",
        "- Quando o usuário pedir para baixar um vídeo, use download_video.",
        "- Quando o usuário compartilhar informações pessoais sobre si mesmo, use set_personal_context.",
        "- Quando o usuário quiser mudar o idioma, use set_language.",
        "- Quando o usuário perguntar o que você sabe sobre ele, use get_my_profile.",
        "- Você pode chamar múltiplas ferramentas em uma única resposta se a mensagem "
        "contiver múltiplas intenções (ex: 'pesquise X e me lembre amanhã').",
        "",
        f"Data/hora atual: {_now_str(user_tz)} ({user_tz}).",
    ]

    if profile:
        if profile.get("personal_context"):
            parts.append(f"\nContexto pessoal do usuário:\n{profile['personal_context']}")
        if profile.get("language"):
            parts.append(f"\nIdioma preferido: {profile['language']}. Responda nesse idioma.")

    return "\n".join(parts)


@dataclass
class AgentResult:
    text: str | None = None
    image_bytes: bytes | None = None
    response_id: str | None = None
    tools_called: list[str] | None = None
    iterations: int = 0


async def run_agent(
    user_input: str | list,
    previous_response_id: str | None = None,
    phone: str | None = None,
    scheduler: object = None,
) -> AgentResult:
    """Execute the agentic loop: model decides tools, we execute, repeat until done."""
    from aisha.user_profile import get_profile

    profile = await get_profile(phone) if phone else None
    user_tz = (profile or {}).get("timezone") or USER_TIMEZONE
    instructions = _build_system_prompt(profile, user_tz)

    ctx = ToolContext(
        phone=phone or "",
        scheduler=scheduler,
        user_tz=user_tz,
        base_url=BASE_URL,
    )

    tools_called: list[str] = []
    current_input = user_input

    kwargs: dict = {
        "model": _MODEL,
        "instructions": instructions,
        "input": current_input,
        "tools": TOOL_DEFINITIONS,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    log.info(f"Agent starting: input={str(user_input)[:120]} (prev={previous_response_id})")

    for iteration in range(1, _MAX_ITERATIONS + 1):
        response = await _client.responses.create(**kwargs)

        function_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not function_calls:
            break

        tool_outputs = []
        for call in function_calls:
            log.info(f"Agent iteration {iteration}: calling {call.name}")
            tools_called.append(call.name)

            result_str = await execute_tool(call.name, call.arguments, ctx)
            tool_outputs.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": result_str,
            })

        kwargs = {
            "model": _MODEL,
            "instructions": instructions,
            "input": tool_outputs,
            "tools": TOOL_DEFINITIONS,
            "previous_response_id": response.id,
        }

    text_parts: list[str] = []
    image_bytes: bytes | None = None

    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_parts.append(content.text)
        elif item.type == "image_generation_call":
            image_bytes = base64.b64decode(item.result)

    result = AgentResult(
        text="\n".join(text_parts) if text_parts else None,
        image_bytes=image_bytes,
        response_id=response.id,
        tools_called=tools_called if tools_called else None,
        iterations=iteration,
    )

    log.info(
        f"Agent finished: iterations={result.iterations}, "
        f"tools={result.tools_called}, "
        f"text={bool(result.text)}, image={bool(result.image_bytes)}, "
        f"id={result.response_id}"
    )
    return result
