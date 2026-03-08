"""Aisha chat skill using OpenAI Responses API.

Routing strategy:
  - gpt-4.1-mini  → classify complexity (cheap, fast)
  - gpt-4.1       → simple/casual messages (greetings, direct questions)
  - gpt-5.4       → complex messages (reasoning, web search, image generation)
"""

import base64
import logging
import re
from dataclasses import dataclass

from openai import AsyncOpenAI

from config import OPENAI_API_KEY

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Você é Aisha, uma assistente pessoal inteligente e amigável. \
Responda de forma objetiva e útil. Use o idioma do usuário."""

_CLASSIFIER_PROMPT = """\
Classify the user message as SIMPLE or COMPLEX.

SIMPLE: casual chat, greetings, short direct questions, small talk, \
confirmations, reactions (e.g. "oi", "blz?", "como vai?", "obrigado", \
"que legal", "tudo bem?", "o que é X?", "me conta uma piada").

COMPLEX: requires web search, image generation, multi-step reasoning, \
calculations, writing/editing long texts, research, technical questions, \
code, planning, or anything that benefits from a more capable model.

Reply with exactly one word: SIMPLE or COMPLEX."""

_NEW_SESSION_PATTERNS = [
    r"\bnova conversa\b",
    r"\bnovo assunto\b",
    r"\bmudar de assunto\b",
    r"\breseta\b",
    r"\breset\b",
    r"\bvamos falar sobre outra coisa\b",
]

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


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


async def _classify(user_input: str) -> str:
    """Return 'SIMPLE' or 'COMPLEX' using gpt-4.1-mini as a cheap classifier."""
    response = await _client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": _CLASSIFIER_PROMPT},
            {"role": "user", "content": user_input},
        ],
        max_tokens=5,
        temperature=0,
    )
    label = response.choices[0].message.content.strip().upper()
    return "SIMPLE" if label.startswith("SIMPLE") else "COMPLEX"


async def chat(
    user_input: str,
    previous_response_id: str | None = None,
) -> ChatResult:
    """Route to gpt-4.1 or gpt-5.4 based on message complexity."""
    complexity = await _classify(user_input)
    log.info(f"Chat [{complexity}]: {user_input[:120]} (prev={previous_response_id})")

    if complexity == "SIMPLE":
        return await _chat_simple(user_input, previous_response_id)
    else:
        return await _chat_complex(user_input, previous_response_id)


async def _chat_simple(
    user_input: str,
    previous_response_id: str | None,
) -> ChatResult:
    """Handle simple messages with gpt-4.1 via Responses API."""
    kwargs: dict = {
        "model": "gpt-4.1",
        "instructions": SYSTEM_PROMPT,
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


async def _chat_complex(
    user_input: str,
    previous_response_id: str | None,
) -> ChatResult:
    """Handle complex messages with gpt-5.4 + web_search + image_generation."""
    kwargs: dict = {
        "model": "gpt-5.4",
        "instructions": SYSTEM_PROMPT,
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
