"""Refine raw transcriptions using an LLM."""

from openai import AsyncOpenAI

from aisha.config import OPENAI_API_KEY

SYSTEM_PROMPT = """\
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

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def refine_transcription(raw_text: str) -> str:
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
