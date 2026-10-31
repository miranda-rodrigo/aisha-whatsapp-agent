"""Nível 3: análise da conversa com citações obrigatórias por mensagem."""

from __future__ import annotations

import json
from pathlib import Path

from . import costs
from .config import LLM_MODEL, load_env
from .context import conversation_text
from .model import known_ids, strip_invalid_citations, validate_analise

_SYSTEM = (
    "Você analisa uma conversa de WhatsApp em português e devolve APENAS JSON válido. "
    "Toda afirmação precisa citar os ids das mensagens de origem (formato msg-...), "
    "copiados exatamente do texto. Não invente ids nem fatos. Formato:\n"
    "{\n"
    '  "resumo": "um parágrafo",\n'
    '  "linha_do_tempo": [{"texto": "...", "mensagens": ["msg-..."]}],\n'
    '  "valores": [{"texto": "valor/plano/condição cotados", "mensagens": ["msg-..."]}],\n'
    '  "compromissos": [{"texto": "quem prometeu o quê", "mensagens": ["msg-..."]}],\n'
    '  "pendencias": [{"texto": "o que ficou em aberto", "mensagens": ["msg-..."]}]\n'
    "}"
)


def analyze_conversation(conv: dict, out_dir: Path, *, model: str = LLM_MODEL) -> dict:
    load_env()
    from openai import OpenAI
    client = OpenAI()
    objetivo = conv.get("objetivo") or "entender a conversa"
    comments = []
    for msg in conv["messages"]:
        for media in msg["media"]:
            if media.get("comentario"):
                comments.append(f"{msg['id']} [{media['filename']}]: {media['comentario']}")
    user = (
        f"Objetivo da análise: {objetivo}\n\n"
        f"Conversa completa (áudios transcritos, ids entre parênteses):\n---\n"
        f"{conversation_text(conv)}\n---\n\n"
        f"Comentários já gerados sobre as mídias:\n---\n" + "\n".join(comments) + "\n---"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        max_tokens=4000,
    )
    inp, out = costs.usage_tokens(getattr(resp, "usage", None))
    costs.record(out_dir, etapa="nivel3_analise", model=model,
                 input_tokens=inp, output_tokens=out, item="analise")
    analise = json.loads(resp.choices[0].message.content or "{}")

    ids = known_ids(conv)
    problems = validate_analise(analise, ids)
    analise = strip_invalid_citations(analise, ids)
    avisos = []
    if problems:
        avisos.append(
            f"{len(problems)} afirmações foram descartadas ou tiveram citações removidas "
            "por apontarem para mensagens inexistentes.")
    analise["avisos"] = avisos
    conv["analise"] = analise
    return analise
