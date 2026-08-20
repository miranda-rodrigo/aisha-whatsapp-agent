"""Refine raw transcriptions using gpt-5.6-luna (reasoning none)."""

from aisha.openai_chat import chunk_text, map_chat_chunks_async
from aisha.models import CHAT_MODEL

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


def _user_for_chunk(index: int, chunk: str, total: int) -> str:
    if total == 1:
        return chunk
    return (
        f"Parte {index + 1} de {total} da transcrição bruta. "
        f"Edite só este trecho, sem resumir.\n\n{chunk}"
    )


async def refine_transcription(raw_text: str) -> str:
    raw = (raw_text or "").strip()
    if not raw:
        raise RuntimeError("Texto bruto vazio; não há o que melhorar.")
    chunks = chunk_text(raw)
    pieces = await map_chat_chunks_async(_SYSTEM_PROMPT, chunks, _user_for_chunk)
    improved = "\n\n".join(pieces).strip()
    if not improved:
        raise RuntimeError("O modelo devolveu resposta vazia.")
    return improved


def refine_model_id() -> str:
    return CHAT_MODEL
