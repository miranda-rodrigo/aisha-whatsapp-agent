"""Aisha agentic loop using OpenAI Responses API with tool calling.

The model receives all available tools and autonomously decides which to
invoke, in what order, and how many times.
"""

import asyncio
import base64
import logging
import zoneinfo
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI

from aisha.config import BASE_URL, OPENAI_API_KEY, USER_TIMEZONE
from aisha.models import AGENT_MODEL, FAST_MODEL
from aisha.tools import TOOL_DEFINITIONS, ToolContext, execute_tool

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

_MAX_ITERATIONS = 10
_COMPACT_THRESHOLD = 80_000

_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
             "sexta-feira", "sábado", "domingo"]
_MONTHS = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
           "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

_skills_path = Path(__file__).parents[1] / "skills.md"
_SKILLS_SUMMARY = ""
if _skills_path.exists():
    _SKILLS_SUMMARY = _skills_path.read_text(encoding="utf-8")[:4000]


def _now_str(user_tz: str) -> str:
    now = datetime.now(zoneinfo.ZoneInfo(user_tz))
    wd = _WEEKDAYS[now.weekday()]
    month = _MONTHS[now.month]
    return f"{wd}, {now.day} de {month} de {now.year}, {now.strftime('%H:%M')}"


def _build_system_prompt(
    profile: dict | None,
    user_tz: str,
    active_reminders: list[dict] | None = None,
    memories: list[dict] | None = None,
) -> str:
    stable = [
        "Você é Aisha, uma assistente pessoal orientada a tarefas que opera via WhatsApp.",
        "Missão: tirar tarefas da cabeça do usuário com o mínimo de fricção, no app que ele já usa todos os dias.",
        "Você NÃO é um chatbot para bate-papo. Seu papel é executar ações concretas.",
        "",
        "PRINCÍPIOS:",
        "1. Ação > conversa. Cada interação termina em algo feito ou uma pergunta objetiva.",
        "2. WhatsApp é a interface inteira. Não peça apps, logins ou dashboards.",
        "3. Ambiguidade gera pergunta, nunca suposição. Limite gera honestidade: 'Não tenho essa habilidade.'",
        "4. Proatividade agendada é o valor máximo — lembretes e tarefas que você inicia.",
        "5. Memória a serviço do usuário: lembre para personalizar; o usuário pode ver e apagar o que você sabe.",
        "",
        "VOZ: direta, sem alongar conversa. Emojis só funcionais (✅ 📋 ⏳). Idioma do usuário.",
        "",
        "COMPORTAMENTO PADRÃO:",
        "- AÇÃO CLARA: execute diretamente (criar lembrete, pesquisar, resumir, gerar imagem).",
        "- MENSAGEM AMBÍGUA: conteúdo encaminhado sem instrução → 'O que você quer que eu faça com isso?'",
        "- PERGUNTA DIRETA: responda. Buscar informação é uma ação implícita.",
        "- SAUDAÇÃO: breve ('Oi! Como posso te ajudar?'). NÃO estenda a conversa.",
        "- PEDIDO IMPOSSÍVEL: 'Não tenho essa habilidade.' Não invente capacidades.",
        "",
        "REGRAS DE USO DAS FERRAMENTAS:",
        "- Use o idioma do usuário (ou o idioma preferido dele, se configurado).",
        "- Quando a resposta exigir informações atualizadas, use web_search.",
        "- Quando o usuário pedir para gerar ou editar uma imagem, use image_generation.",
        "- Quando o usuário pedir um lembrete, verifique os LEMBRETES ATIVOS abaixo antes de agir:",
        "    * Se já existe um lembrete sobre o mesmo assunto/evento, use edit_reminder.",
        "    * Só use create_reminder se o lembrete é claramente novo.",
        "- Quando o usuário pedir uma tarefa recorrente/agendada, use create_scheduled_task.",
        "- YouTube: você TEM a skill analyze_youtube_video (transcrever, resumir, pontos-chave). "
        "Áudio do WhatsApp é outra skill (Whisper). Não diga que só transcreve áudio.",
        "- Link do YouTube COM instrução na mesma mensagem: execute direto (analyze_youtube_video ou download_video).",
        "- Link do YouTube SEM instrução na mensagem, MAS o turno anterior já deixou a intenção clara "
        "(ex: usuário perguntou se você transcreve, pediu transcrição, resumo, download): "
        "NÃO pergunte de novo. Execute com essa intenção. Transcrição de YouTube = analyze_youtube_video "
        "com instruction 'transcreve o vídeo por completo'.",
        "- Link do YouTube SEM instrução E SEM intenção prévia na conversa: aí sim pergunte o que fazer.",
        "- Se não conseguir transcrever (vídeo privado ou live): diga o limite com honestidade. "
        "Não invente que a skill não existe.",
        "- Vídeo longo (>25 min): analyze_youtube_video já devolve um RESUMO no campo analysis "
        "e um download_link do TXT com a transcrição completa. Encaminhe os dois. "
        "Não diga que o vídeo é longo demais e não peça timestamp.",
        "- Qualquer outro link: mesma lógica de intenção prévia. Sem intenção, pergunte. Com intenção, use read_webpage.",
        "- Para baixar vídeos, use download_video.",
        "- Quando o usuário compartilhar informações pessoais duradouras, use save_memory.",
        "- Para mudar idioma, use set_language. Para consultar perfil, use get_my_profile.",
        "- 'O que você sabe de mim?' → get_my_profile + list_memories.",
        "- 'Esqueça isso' / 'apaga essa memória' → forget_memory.",
        "- Você pode chamar múltiplas ferramentas em uma única resposta quando houver múltiplas intenções.",
    ]
    if _SKILLS_SUMMARY:
        stable.append("\nRESUMO DAS HABILIDADES (referência):\n" + _SKILLS_SUMMARY)

    dynamic = [f"\nData/hora atual: {_now_str(user_tz)} ({user_tz})."]

    if profile:
        if profile.get("personal_context"):
            dynamic.append(f"\nContexto pessoal do usuário:\n{profile['personal_context']}")
        if profile.get("language"):
            dynamic.append(f"\nIdioma preferido: {profile['language']}. Responda nesse idioma.")

    if memories:
        lines = ["\nMEMÓRIAS RELEVANTES DO USUÁRIO:"]
        for m in memories:
            lines.append(f"  - {m['content']}")
        dynamic.append("\n".join(lines))

    if active_reminders:
        lines = ["\nLEMBRETES ATIVOS DO USUÁRIO (use edit_reminder antes de criar um novo sobre o mesmo assunto):"]
        for r in active_reminders:
            recur = " [recorrente]" if r.get("is_recurring") else ""
            lines.append(f"  #{r['number']}. {r['message']} — {r['datetime_display']}{recur}")
        dynamic.append("\n".join(lines))
    else:
        dynamic.append("\nLEMBRETES ATIVOS DO USUÁRIO: nenhum.")

    return "\n".join(stable + dynamic)


@dataclass
class AgentResult:
    text: str | None = None
    image_bytes: bytes | None = None
    response_id: str | None = None
    tools_called: list[str] | None = None
    iterations: int = 0


def _parse_response(response) -> tuple[str | None, bytes | None]:
    text_parts: list[str] = []
    image_bytes: bytes | None = None
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_parts.append(content.text)
        elif item.type == "image_generation_call":
            image_bytes = base64.b64decode(item.result)
    return ("\n".join(text_parts) if text_parts else None, image_bytes)


async def run_fast_path(
    user_input: str,
    previous_response_id: str | None = None,
    phone: str | None = None,
) -> AgentResult:
    """Cheap path for greetings and thanks — no tools, Luna only."""
    from aisha.user_profile import get_profile

    profile = await get_profile(phone) if phone else None
    user_tz = (profile or {}).get("timezone") or USER_TIMEZONE
    instructions = _build_system_prompt(profile, user_tz)
    kwargs: dict = {
        "model": FAST_MODEL,
        "instructions": instructions,
        "input": user_input,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id
    response = await _client.responses.create(**kwargs)
    text, image_bytes = _parse_response(response)
    return AgentResult(text=text, image_bytes=image_bytes, response_id=response.id, iterations=1)


async def run_agent(
    user_input: str | list,
    previous_response_id: str | None = None,
    phone: str | None = None,
    scheduler: object = None,
) -> AgentResult:
    """Execute the agentic loop: model decides tools, we execute, repeat until done."""
    from aisha.user_profile import get_profile
    from aisha.skills.reminder_store import get_reminders
    from aisha.skills.reminder import _fmt_local
    from aisha.skills.memory_store import search_memories
    from datetime import datetime as _datetime

    profile = await get_profile(phone) if phone else None
    user_tz = (profile or {}).get("timezone") or USER_TIMEZONE

    active_reminders: list[dict] | None = None
    if phone:
        try:
            rows = await get_reminders(phone)
            if rows:
                active_reminders = []
                for i, row in enumerate(rows, 1):
                    dt_utc = _datetime.fromisoformat(row["scheduled_at"])
                    active_reminders.append({
                        "number": i,
                        "message": row["message"],
                        "datetime_display": _fmt_local(dt_utc, row.get("timezone") or user_tz),
                        "is_recurring": row.get("is_recurring", False),
                    })
        except Exception:
            log.warning("Failed to fetch active reminders for system prompt", exc_info=True)

    memories: list[dict] | None = None
    if phone and isinstance(user_input, str):
        try:
            memories = await search_memories(phone, user_input, limit=5)
        except Exception:
            log.warning("Failed to search memories for system prompt", exc_info=True)

    instructions = _build_system_prompt(profile, user_tz, active_reminders, memories)

    ctx = ToolContext(
        phone=phone or "",
        scheduler=scheduler,
        user_tz=user_tz,
        base_url=BASE_URL,
    )

    tools_called: list[str] = []

    kwargs: dict = {
        "model": AGENT_MODEL,
        "instructions": instructions,
        "input": user_input,
        "tools": TOOL_DEFINITIONS,
        "context_management": [
            {"type": "compaction", "compact_threshold": _COMPACT_THRESHOLD},
        ],
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    log.info(f"Agent starting: input={str(user_input)[:120]} (prev={previous_response_id})")

    response = None
    iteration = 0
    for iteration in range(1, _MAX_ITERATIONS + 1):
        response = await _client.responses.create(**kwargs)

        function_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not function_calls:
            break

        async def _run_one(call):
            log.info(f"Agent iteration {iteration}: calling {call.name}")
            result_str = await execute_tool(call.name, call.arguments, ctx)
            return {
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": result_str,
                "name": call.name,
            }

        results = await asyncio.gather(*[_run_one(call) for call in function_calls])
        tool_outputs = []
        for item in results:
            tools_called.append(item.pop("name"))
            tool_outputs.append(item)

        kwargs = {
            "model": AGENT_MODEL,
            "instructions": instructions,
            "input": tool_outputs,
            "tools": TOOL_DEFINITIONS,
            "previous_response_id": response.id,
            "context_management": [
                {"type": "compaction", "compact_threshold": _COMPACT_THRESHOLD},
            ],
        }

    text, image_bytes = _parse_response(response)
    result = AgentResult(
        text=text,
        image_bytes=image_bytes,
        response_id=response.id if response else None,
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
