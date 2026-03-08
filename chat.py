"""Aisha chat skill using OpenAI Responses API (GPT-5.4)."""

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


async def chat(
    user_input: str,
    previous_response_id: str | None = None,
) -> ChatResult:
    """Send user input to GPT-5.4 with web_search and image_generation tools."""
    log.info(f"Chat request: {user_input[:120]} (prev={previous_response_id})")

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
        f"Chat result: text={bool(result.text)}, "
        f"image={bool(result.image_bytes)}, id={result.response_id}"
    )
    return result
