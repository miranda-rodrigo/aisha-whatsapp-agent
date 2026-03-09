"""Refine raw transcriptions using an LLM."""

import logging

from google import genai
from google.genai import types
from google.genai.errors import ServerError

from aisha.config import GEMINI_API_KEY

log = logging.getLogger(__name__)

_PRIMARY_MODEL = "gemini-2.5-flash"
_FALLBACK_MODEL = "gemini-2.0-flash-lite"

_SYSTEM_PROMPT = """\
Atue como um editor de textos especializado em transcrições. \
Sua tarefa é converter a fala natural abaixo em uma linguagem escrita clara e fluida.

Diretrizes:

Remova: Vícios de linguagem, hesitações (hã, é...), repetições desnecessárias e preenchimentos.

Refine: Corrija erros gramaticais e pontuação. Se o falante se autocorrigir, \
mantenha apenas a versão final/correta.

Preserve: O idioma original, o tom e a extensão aproximada do texto. \
Ou seja, se o texto está em inglês, a transcrição melhorada deve ser em inglês. \
Se for em português, o texto melhorado deve ser em português. \
Se for multi-língue, o texto corrigido deverá ser multi-língue.

Foco: O resultado deve parecer um texto escrito intencionalmente, sem perder a voz do autor.

Retorne APENAS o texto refinado, sem explicações ou comentários."""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


async def _generate(model: str, raw_text: str) -> str:
    response = await _get_client().aio.models.generate_content(
        model=model,
        contents=raw_text,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.3,
        ),
    )
    return response.text.strip()


async def refine_transcription(raw_text: str) -> str:
    try:
        return await _generate(_PRIMARY_MODEL, raw_text)
    except ServerError as e:
        if e.code == 503:
            log.warning(f"Primary model {_PRIMARY_MODEL} unavailable (503), trying fallback {_FALLBACK_MODEL}")
            return await _generate(_FALLBACK_MODEL, raw_text)
        raise
