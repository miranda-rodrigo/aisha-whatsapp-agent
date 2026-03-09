"""Refine raw transcriptions using an LLM."""

from google import genai
from google.genai import types

from aisha.config import GEMINI_API_KEY

_MODEL = "gemini-3.1-flash-lite-preview"

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


async def refine_transcription(raw_text: str) -> str:
    response = await _get_client().aio.models.generate_content(
        model=_MODEL,
        contents=raw_text,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.3,
        ),
    )
    return response.text.strip()
