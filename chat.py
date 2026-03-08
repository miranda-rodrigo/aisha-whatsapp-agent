"""Aisha chat skill using OpenAI Responses API (GPT-5.4)."""

import base64
import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from config import OPENAI_API_KEY

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Você é Aisha, uma assistente pessoal inteligente e amigável. \
Responda de forma objetiva e útil. Use o idioma do usuário."""

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


@dataclass
class ChatResult:
    text: str | None = None
    image_bytes: bytes | None = None


async def chat(user_input: str) -> ChatResult:
    """Send user input to GPT-5.4 with web_search and image_generation tools."""
    log.info(f"Chat request: {user_input[:120]}")

    response = await _client.responses.create(
        model="gpt-5.4",
        instructions=SYSTEM_PROMPT,
        input=user_input,
        tools=[
            {"type": "web_search"},
            {"type": "image_generation"},
        ],
    )

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
    )
    log.info(f"Chat result: text={bool(result.text)}, image={bool(result.image_bytes)}")
    return result
