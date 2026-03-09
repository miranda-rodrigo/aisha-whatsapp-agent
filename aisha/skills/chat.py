"""Aisha chat skill using OpenAI Responses API.

Routing strategy:
  - gemini-3.1-flash-lite-preview → classify complexity (cheap, fast)
  - gpt-4.1-mini  → detect self-awareness sub-action (structured output)
  - gpt-4.1       → simple/casual messages (greetings, direct questions)
  - gpt-4.1       → self-awareness questions (skills/capabilities, injected from aisha_skills.md)
  - gpt-5.4       → complex messages (reasoning, web search, image generation)
  - gpt-5.4 + image_generation → image editing/generation from user photos
  - gpt-4.1       → document Q&A (document text injected as context)
"""

import base64
import logging
import re
import zoneinfo
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from aisha.config import GEMINI_API_KEY, OPENAI_API_KEY, USER_TIMEZONE

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Você é Aisha, uma assistente pessoal inteligente e amigável. \
Responda de forma objetiva e útil. Use o idioma do usuário."""

_CLASSIFIER_PROMPT = """\
Classify the user message as SIMPLE, COMPLEX, or SELF.

SIMPLE: casual chat, greetings, short direct questions, small talk, \
confirmations, reactions (e.g. "oi", "blz?", "como vai?", "obrigado", \
"que legal", "tudo bem?", "o que é X?", "me conta uma piada").

COMPLEX: requires web search, image generation, multi-step reasoning, \
calculations, writing/editing long texts, research, technical questions, \
code, planning, or anything that benefits from a more capable model.

SELF: questions about Aisha herself — what she can do, her skills or abilities, \
how to use a feature, her limitations, who she is, how she works. \
This includes questions like "o que você faz?", "você consegue X?", \
"como funciona a transcrição?", "quais são seus skills?", "quem é você?", \
"como envio um documento?", "você pode criar lembretes?", \
"você analisa vídeos do YouTube?", "posso modificar um lembrete?", \
"como edito um lembrete?", "dá pra mudar o horário?", \
"como cancelo?", "você faz lembretes recorrentes?", \
"como funciona o lembrete?", "quais são as funções?", \
"o que mais você sabe fazer?", "me explica como usar".

Important distinction:
- Questions about capability or instructions are SELF.
- Actual operational requests to create, list, edit, cancel, or modify reminders \
  or scheduled tasks are NOT SELF.
- Examples that are NOT SELF: "modifique a tarefa agendada 1", \
  "muda o lembrete 2 para 11h", "quais são minhas tarefas agendadas?".

Reply with exactly one word: SIMPLE, COMPLEX, or SELF."""

_NEW_SESSION_PATTERNS = [
    r"\bnova conversa\b",
    r"\bnovo assunto\b",
    r"\bmudar de assunto\b",
    r"\breseta\b",
    r"\breset\b",
    r"\bvamos falar sobre outra coisa\b",
]

_IMAGE_INSTRUCTIONS = """\
O usuário enviou uma imagem e está dando instruções sobre o que fazer com ela. \
Execute a instrução do usuário sobre a imagem. Isso pode incluir: melhorar a imagem, \
editar elementos, mudar estilo, gerar uma nova imagem baseada nesta, descrever a imagem, \
extrair texto, remover fundo, etc. Use a ferramenta de geração de imagem quando apropriado."""

_skills_path = Path(__file__).parents[2] / "skills.md"
_SKILLS_CONTENT: str = _skills_path.read_text(encoding="utf-8") if _skills_path.exists() else ""

_SELF_INSTRUCTIONS = f"""\
{SYSTEM_PROMPT}

Você tem acesso ao seu próprio guia de habilidades abaixo. Use-o para responder \
perguntas sobre o que você sabe fazer, como usar cada funcionalidade e suas limitações. \
Responda de forma amigável e concisa. Se o usuário pedir detalhes de uma funcionalidade, \
dê exemplos práticos de uso.

Funcionalidades especiais que você deve conhecer:
- O usuário pode te enviar um contexto pessoal (quem ele é, preferências, etc.) e você \
vai lembrar para sempre. Ele pode atualizar esse contexto quando quiser.
- O usuário pode pedir para mudar o idioma da conversa (ex: "vamos falar em inglês").
- O usuário pode perguntar "o que você sabe de mim?" e você lista tudo: contexto pessoal, \
lembretes ativos, preferências e estatísticas de uso.

---
{_SKILLS_CONTENT}
"""

_SELF_ACTION_PROMPT = """\
Analyze the user message and determine the self-awareness action.

- "skills": asking about Aisha's capabilities, how to use features, who she is
- "set_context": user is providing personal context about themselves (name, job, \
preferences, personality instructions for Aisha, etc.)
- "set_language": user wants to change the conversation language
- "list_profile": user wants to know what Aisha knows about them, their data, profile

Extract context_to_save when action is set_context (the full personal context text).
Extract language_to_save when action is set_language (e.g. "english", "português", "español")."""


class SelfAction(BaseModel):
    action: Literal["skills", "set_context", "set_language", "list_profile"]
    context_to_save: str | None = Field(None, description="Personal context to save")
    language_to_save: str | None = Field(None, description="Language preference to save")


_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

_gemini_client: genai.Client | None = None
_GEMINI_CLASSIFIER_MODEL = "gemini-3.1-flash-lite-preview"


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


@dataclass
class ChatResult:
    text: str | None = None
    image_bytes: bytes | None = None
    response_id: str | None = None


def wants_new_session(text: str) -> bool:
    """Check if the user is explicitly requesting a fresh conversation."""
    for pattern in _NEW_SESSION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


async def classify(user_input: str) -> str:
    """Return 'SIMPLE', 'COMPLEX', or 'SELF' using Gemini Flash Lite as a cheap classifier."""
    response = await _get_gemini_client().aio.models.generate_content(
        model=_GEMINI_CLASSIFIER_MODEL,
        contents=user_input,
        config=genai_types.GenerateContentConfig(
            system_instruction=_CLASSIFIER_PROMPT,
            max_output_tokens=5,
            temperature=0,
        ),
    )
    label = response.text.strip().upper()
    if label.startswith("SELF"):
        return "SELF"
    return "SIMPLE" if label.startswith("SIMPLE") else "COMPLEX"


_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_MONTHS = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _now_str() -> str:
    """Current datetime formatted in Portuguese, locale-independent."""
    now = datetime.now(zoneinfo.ZoneInfo(USER_TIMEZONE))
    wd = _WEEKDAYS[now.weekday()]
    month = _MONTHS[now.month]
    return f"{wd}, {now.day} de {month} de {now.year}, {now.strftime('%H:%M')}"


def _build_instructions(base: str, profile: dict | None) -> str:
    """Append current datetime and user profile context to base instructions."""
    parts = [
        base,
        f"\nData/hora atual: {_now_str()} ({USER_TIMEZONE}).",
    ]
    if profile:
        if profile.get("personal_context"):
            parts.append(f"\nContexto pessoal do usuário:\n{profile['personal_context']}")
        if profile.get("language"):
            parts.append(f"\nIdioma preferido do usuário: {profile['language']}. Responda nesse idioma.")
    return "\n".join(parts)


async def chat(
    user_input: str,
    previous_response_id: str | None = None,
    phone: str | None = None,
    complexity: str | None = None,
) -> ChatResult:
    """Route to gpt-4.1, gpt-5.4, or self-awareness handler based on message classification."""
    from aisha.user_profile import get_profile

    profile = await get_profile(phone) if phone else None
    if complexity is None:
        complexity = await classify(user_input)
    log.info(f"Chat [{complexity}]: {user_input[:120]} (prev={previous_response_id})")

    if complexity == "SELF":
        return await _chat_self(user_input, previous_response_id, phone, profile)
    elif complexity == "SIMPLE":
        return await _chat_simple(user_input, previous_response_id, profile)
    else:
        return await _chat_complex(user_input, previous_response_id, profile)


async def _chat_simple(
    user_input: str,
    previous_response_id: str | None,
    profile: dict | None = None,
) -> ChatResult:
    """Handle simple messages with gpt-4.1 via Responses API."""
    kwargs: dict = {
        "model": "gpt-4.1",
        "instructions": _build_instructions(SYSTEM_PROMPT, profile),
        "input": user_input,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = await _client.responses.create(**kwargs)

    text_parts = [
        content.text
        for item in response.output
        if item.type == "message"
        for content in item.content
        if content.type == "output_text"
    ]

    result = ChatResult(
        text="\n".join(text_parts) if text_parts else None,
        response_id=response.id,
    )
    log.info(f"Simple result: text={bool(result.text)}, id={result.response_id}")
    return result


async def _detect_self_action(user_input: str) -> SelfAction:
    """Detect sub-intent within SELF category using structured output."""
    response = await _client.beta.chat.completions.parse(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": _SELF_ACTION_PROMPT},
            {"role": "user", "content": user_input},
        ],
        response_format=SelfAction,
        temperature=0,
    )
    return response.choices[0].message.parsed


async def _chat_self(
    user_input: str,
    previous_response_id: str | None,
    phone: str | None = None,
    profile: dict | None = None,
) -> ChatResult:
    """Handle self-awareness questions, profile customization, and user data queries."""
    from aisha.skills.reminder_store import get_reminders
    from aisha.user_profile import get_profile, upsert_context, upsert_language

    action = await _detect_self_action(user_input)
    log.info(f"Self action: {action.action} for {phone}")

    if action.action == "set_context" and action.context_to_save and phone:
        existing = profile.get("personal_context", "") if profile else ""
        if existing:
            new_context = f"{existing}\n{action.context_to_save}"
        else:
            new_context = action.context_to_save
        await upsert_context(phone, new_context)

    if action.action == "set_language" and action.language_to_save and phone:
        await upsert_language(phone, action.language_to_save)

    extra_user_data = ""
    if action.action == "list_profile" and phone:
        from aisha.skills.scheduled_task_store import get_tasks

        fresh_profile = await get_profile(phone)
        reminders = await get_reminders(phone)
        scheduled_tasks = await get_tasks(phone)

        parts = ["DADOS DO USUÁRIO PARA LISTAR:\n"]
        ctx = fresh_profile.get("personal_context", "") if fresh_profile else ""
        lang = fresh_profile.get("language", "") if fresh_profile else ""
        stats = fresh_profile.get("stats", {}) if fresh_profile else {}

        parts.append(f"Contexto pessoal: {ctx if ctx else 'nenhum definido'}")
        parts.append(f"Idioma preferido: {lang if lang else 'nenhum definido (padrão: idioma do usuário)'}")

        if stats:
            stat_lines = [f"  - {k}: {v}" for k, v in stats.items()]
            parts.append("Estatísticas de uso:\n" + "\n".join(stat_lines))
        else:
            parts.append("Estatísticas de uso: nenhuma ainda")

        if reminders:
            reminder_lines = [f"  - {r['message']} ({r['scheduled_at']})" for r in reminders]
            parts.append(f"Lembretes ativos ({len(reminders)}):\n" + "\n".join(reminder_lines))
        else:
            parts.append("Lembretes ativos: nenhum")

        if scheduled_tasks:
            task_lines = [f"  - {t['name']} (cron: {t['cron_expression']})" for t in scheduled_tasks]
            parts.append(f"Tarefas agendadas ({len(scheduled_tasks)}):\n" + "\n".join(task_lines))
        else:
            parts.append("Tarefas agendadas: nenhuma")

        extra_user_data = "\n".join(parts)

    instructions = _build_instructions(_SELF_INSTRUCTIONS, profile)
    input_text = user_input
    if extra_user_data:
        input_text = f"{user_input}\n\n---\n{extra_user_data}"

    kwargs: dict = {
        "model": "gpt-4.1",
        "instructions": instructions,
        "input": input_text,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = await _client.responses.create(**kwargs)

    text_parts = [
        content.text
        for item in response.output
        if item.type == "message"
        for content in item.content
        if content.type == "output_text"
    ]

    result = ChatResult(
        text="\n".join(text_parts) if text_parts else None,
        response_id=response.id,
    )
    log.info(f"Self result: action={action.action}, text={bool(result.text)}, id={result.response_id}")
    return result


async def _chat_complex(
    user_input: str,
    previous_response_id: str | None,
    profile: dict | None = None,
) -> ChatResult:
    """Handle complex messages with gpt-5.4 + web_search + image_generation."""
    kwargs: dict = {
        "model": "gpt-5.4",
        "instructions": _build_instructions(SYSTEM_PROMPT, profile),
        "input": user_input,
        "tools": [
            {"type": "web_search"},
            {"type": "image_generation"},
        ],
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = await _client.responses.create(**kwargs)

    text_parts: list[str] = []
    image_bytes: bytes | None = None

    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_parts.append(content.text)
        elif item.type == "image_generation_call":
            image_bytes = base64.b64decode(item.result)

    result = ChatResult(
        text="\n".join(text_parts) if text_parts else None,
        image_bytes=image_bytes,
        response_id=response.id,
    )
    log.info(
        f"Complex result: text={bool(result.text)}, "
        f"image={bool(result.image_bytes)}, id={result.response_id}"
    )
    return result


async def chat_with_image(
    user_input: str,
    image_bytes: bytes,
    mime_type: str,
    previous_response_id: str | None = None,
) -> ChatResult:
    """Process user instruction together with an image via Responses API."""
    b64_data = base64.b64encode(image_bytes).decode()

    multimodal_input = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": f"data:{mime_type};base64,{b64_data}",
                },
                {"type": "input_text", "text": user_input},
            ],
        }
    ]

    kwargs: dict = {
        "model": "gpt-5.4",
        "instructions": _build_instructions(f"{SYSTEM_PROMPT}\n\n{_IMAGE_INSTRUCTIONS}", None),
        "input": multimodal_input,
        "tools": [{"type": "image_generation"}],
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = await _client.responses.create(**kwargs)

    text_parts: list[str] = []
    result_image: bytes | None = None

    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_parts.append(content.text)
        elif item.type == "image_generation_call":
            result_image = base64.b64decode(item.result)

    result = ChatResult(
        text="\n".join(text_parts) if text_parts else None,
        image_bytes=result_image,
        response_id=response.id,
    )
    log.info(
        f"Image chat result: text={bool(result.text)}, "
        f"image={bool(result.image_bytes)}, id={result.response_id}"
    )
    return result


_DOCUMENT_INSTRUCTIONS = """\
O usuário enviou um documento. O conteúdo completo está abaixo. \
Responda perguntas sobre ele com precisão, citando trechos quando relevante. \
Se o usuário não fizer uma pergunta, faça um resumo estruturado."""

_WEBPAGE_INSTRUCTIONS = """\
O usuário enviou um link de página web. O conteúdo foi extraído abaixo em markdown. \
Execute a instrução do usuário sobre esse conteúdo. \
Se nenhuma instrução for dada, faça um resumo conciso e estruturado dos pontos principais."""


async def chat_with_document(
    document_text: str,
    user_instruction: str | None,
    previous_response_id: str | None = None,
) -> ChatResult:
    """Summarize a document and persist the session so follow-up questions work."""
    user_message = f"DOCUMENTO:\n\n{document_text}"
    if user_instruction:
        user_message = f"INSTRUÇÃO: {user_instruction}\n\n{user_message}"

    kwargs: dict = {
        "model": "gpt-4.1",
        "instructions": _build_instructions(f"{SYSTEM_PROMPT}\n\n{_DOCUMENT_INSTRUCTIONS}", None),
        "input": user_message,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = await _client.responses.create(**kwargs)

    text_parts = [
        content.text
        for item in response.output
        if item.type == "message"
        for content in item.content
        if content.type == "output_text"
    ]

    result = ChatResult(
        text="\n".join(text_parts) if text_parts else None,
        response_id=response.id,
    )
    log.info(f"Document chat result: text={bool(result.text)}, id={result.response_id}")
    return result


async def chat_with_webpage(
    page_content: str,
    url: str,
    user_instruction: str | None,
    previous_response_id: str | None = None,
) -> ChatResult:
    """Process a webpage's content with the user's instruction via gpt-4.1."""
    user_message = f"URL: {url}\n\nCONTEÚDO:\n\n{page_content}"
    if user_instruction:
        user_message = f"INSTRUÇÃO: {user_instruction}\n\n{user_message}"

    kwargs: dict = {
        "model": "gpt-4.1",
        "instructions": _build_instructions(f"{SYSTEM_PROMPT}\n\n{_WEBPAGE_INSTRUCTIONS}", None),
        "input": user_message,
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = await _client.responses.create(**kwargs)

    text_parts = [
        content.text
        for item in response.output
        if item.type == "message"
        for content in item.content
        if content.type == "output_text"
    ]

    result = ChatResult(
        text="\n".join(text_parts) if text_parts else None,
        response_id=response.id,
    )
    log.info(f"Webpage chat result: text={bool(result.text)}, id={result.response_id}")
    return result
