"""Nível 2: comentário contextualizado por mídia. A transcrição fica intocada."""

from __future__ import annotations

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import costs
from .config import LLM_MODEL, load_env
from .context import conversation_text, local_window

_WORKERS = 10
_PDF_MAX_PAGES = 3
_PDF_MAX_CHARS = 6000

_SYSTEM = (
    "Você anota mídias de uma conversa de WhatsApp em português. "
    "Comente SOMENTE a mídia indicada, que está marcada com >>> no trecho local. "
    "Escreva UM comentário curto (2 a 3 frases) explicando o que a mídia é e qual "
    "o papel dela na conversa: a que pergunta responde, o que propõe, o que muda. "
    "Use as mensagens imediatamente antes e depois para entender o papel. "
    "Seja factual. Não invente conteúdo que não esteja visível ou no contexto, nem "
    "perguntas que ninguém fez; se o papel não for claro, diga só o que a mídia é. "
    "Não repita a transcrição. Se houver valores, nomes de planos ou condições, cite-os."
)


def _pdf_excerpt(path: Path) -> tuple[str, bytes | None, int]:
    """Texto das primeiras páginas; se escaneado, a página 1 como PNG."""
    import pymupdf
    doc = pymupdf.open(path)
    pages = doc.page_count
    text = "\n".join(doc[i].get_text() for i in range(min(pages, _PDF_MAX_PAGES)))
    image = None
    if len(text.strip()) < 50:
        image = doc[0].get_pixmap(dpi=100).tobytes("png")
    doc.close()
    return text.strip()[:_PDF_MAX_CHARS], image, pages


def _image_part(data: bytes, mime: str) -> dict:
    b64 = base64.b64encode(data).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def annotate_conversation(conv: dict, out_dir: Path, *, model: str = LLM_MODEL,
                          limit: int | None = None) -> int:
    load_env()
    from openai import OpenAI
    client = OpenAI()
    export_dir = Path(conv["export_dir"])
    context = conversation_text(conv)
    objetivo = conv.get("objetivo") or "entender a conversa"
    cache_root = out_dir / "cache" / "comentarios"

    targets = []
    for msg in conv["messages"]:
        for media in msg["media"]:
            if not media["present"] or media["kind"] == "video":
                continue
            if media.get("comentario"):
                continue
            cache = cache_root / (media["filename"] + ".json")
            if cache.exists():
                media["comentario"] = json.loads(cache.read_text(encoding="utf-8"))["comentario"]
                continue
            if media["kind"] == "audio" and not media.get("transcricao"):
                continue  # sem transcrição não há o que comentar
            targets.append((msg, media))
    if limit is not None:
        targets = targets[:limit]
    if not targets:
        return 0

    def work(pair) -> None:
        msg, media = pair
        kind = media["kind"]
        where = (f"A mídia a comentar foi enviada por {msg['sender']} em {msg['date']} "
                 f"às {msg['time']} (mensagem {msg['id']}), arquivo {media['filename']}.")
        parts = [{"type": "text", "text":
                  f"Objetivo de quem pediu a análise: {objetivo}\n\n"
                  f"Conversa completa (áudios já transcritos):\n---\n{context}\n---\n\n"
                  f"Trecho local, com a mídia a comentar marcada por >>>:\n---\n"
                  f"{local_window(conv, msg['id'])}\n---\n\n{where}"}]
        try:
            if kind in ("image", "sticker"):
                data = (export_dir / media["path"]).read_bytes()
                mime = "image/webp" if media["filename"].lower().endswith(".webp") else "image/jpeg"
                parts.append(_image_part(data, mime))
            elif kind == "pdf":
                text, image, pages = _pdf_excerpt(export_dir / media["path"])
                note = (f"O PDF tem {pages} páginas; abaixo o texto das "
                        f"{min(pages, _PDF_MAX_PAGES)} primeiras.")
                if text:
                    parts.append({"type": "text", "text": f"{note}\n---\n{text}\n---"})
                if image is not None:
                    parts.append({"type": "text", "text": "PDF sem texto (escaneado); página 1 como imagem:"})
                    parts.append(_image_part(image, "image/png"))
            elif kind == "audio":
                parts.append({"type": "text", "text":
                              f"É um áudio. Transcrição fiel DESTE áudio: \"{media['transcricao']}\"\n"
                              "Comente apenas o papel dele na conversa, com base nessa transcrição."})
            else:
                parts.append({"type": "text", "text": "Arquivo genérico; comente pelo nome e contexto."})
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": _SYSTEM},
                          {"role": "user", "content": parts}],
                max_tokens=220,
            )
        except Exception as e:
            print(f"  ERRO comentário {media['filename']}: {e}")
            return
        comment = (resp.choices[0].message.content or "").strip()
        if not comment:
            return
        media["comentario"] = comment
        inp, out = costs.usage_tokens(getattr(resp, "usage", None))
        costs.record(out_dir, etapa="nivel2_comentarios", model=model,
                     input_tokens=inp, output_tokens=out, item=media["filename"])
        cache = cache_root / (media["filename"] + ".json")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"comentario": comment, "model": model},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  comentado: {media['filename']}")

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        list(pool.map(work, targets))
    return sum(1 for _, m in targets if m.get("comentario"))
