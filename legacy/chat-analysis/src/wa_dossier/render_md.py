"""Markdown para colar numa IA: conversa.md + fichas de PDF em anexos/."""

from __future__ import annotations

from pathlib import Path

from .config import PRODUCT_NAME

_PDF_MAX_PAGES = 3
_PDF_MAX_CHARS = 6000


def _pdf_text(path: Path) -> tuple[str, int]:
    import pymupdf
    doc = pymupdf.open(path)
    pages = doc.page_count
    text = "\n".join(doc[i].get_text() for i in range(min(pages, _PDF_MAX_PAGES)))
    doc.close()
    return text.strip()[:_PDF_MAX_CHARS], pages


_INSTRUCOES = [
    "## Como usar este documento (instruções para a IA)",
    "",
    "Este arquivo é o registro de uma conversa de WhatsApp, montado a partir da exportação "
    "nativa do aplicativo. Ao responder perguntas sobre ele:",
    "",
    "1. Responda somente com base neste arquivo e nas fichas em `anexos/`. Se a informação "
    "não estiver aqui, responda \"não encontrado\". Não deduza nem complete com conhecimento geral.",
    "2. Para cada afirmação, cite a fonte: o id da mensagem (`msg-...`) e a data e hora. "
    "Ao citar valores, prazos ou compromissos, copie o trecho literal.",
    "3. Separe o que foi dito do que é interpretação. Só a seção \"Conversa\" contém o que "
    "as pessoas disseram. Comentários e a seção \"Análise\" foram gerados por IA, podem "
    "conter erros ou omissões e devem ser conferidos nas mensagens citadas.",
    "4. Transcrições de áudio são automáticas: literais, sem edição, mas podem errar nomes "
    "e números. O áudio original prevalece. Se um número só aparece numa transcrição, avise.",
    "5. Se duas mensagens se contradisserem (por exemplo, um áudio e um texto), aponte as "
    "duas, com os ids, em vez de escolher uma.",
    "6. Dos PDFs anexados, só as primeiras páginas foram extraídas para as fichas. Não "
    "afirme nada sobre o restante do documento.",
    "",
    "Estrutura: cada mensagem aparece como `- **hora remetente** (msg-id): texto`, agrupada "
    "por data (dd/mm/aa). Mídias aparecem logo abaixo da mensagem em que foram enviadas. "
    "\"Ausente da exportação\" significa que o arquivo não veio no zip.",
    "",
]


def _recorte_md(conv: dict) -> str:
    recorte = conv.get("recorte") or {}
    if not recorte.get("desde"):
        return ""
    return (f"- Recorte: desde {recorte['desde']} "
            f"({len(conv['messages'])} de {recorte['mensagens_total']} mensagens). "
            "O período anterior não está neste arquivo.")


def _resumo_midias(conv: dict) -> str:
    counts: dict[str, int] = {}
    ausentes = 0
    for msg in conv["messages"]:
        for media in msg["media"]:
            counts[media["kind"]] = counts.get(media["kind"], 0) + 1
            ausentes += 0 if media["present"] else 1
        ausentes += len(msg.get("omitted") or [])
    tx = sum(1 for m in conv["messages"] for md in m["media"] if md.get("transcricao"))
    partes = [f"{n} {kind}" for kind, n in sorted(counts.items())]
    return (f"- Mídias: {', '.join(partes) or 'nenhuma'} · {tx} áudios transcritos · "
            f"{ausentes} ausentes da exportação")


def _analise_md(analise: dict | None) -> list[str]:
    if not analise:
        return []
    lines = ["## Análise", "",
             "> Gerada por IA a partir da conversa. Pode conter erros ou omissões: "
             "confira cada item nas mensagens citadas antes de usar.", "",
             analise.get("resumo") or "", ""]
    titles = {"linha_do_tempo": "Linha do tempo", "valores": "Valores",
              "compromissos": "Compromissos", "pendencias": "Pendências"}
    for key, title in titles.items():
        items = analise.get(key) or []
        if not items:
            continue
        lines += [f"### {title}", ""]
        for item in items:
            cites = " ".join(f"`{mid}`" for mid in item.get("mensagens") or [])
            lines.append(f"- {item.get('texto', '')} — {cites}")
        lines.append("")
    for aviso in analise.get("avisos") or []:
        lines += [f"> Aviso: {aviso}", ""]
    return lines


def render_md(conv: dict, out_dir: Path) -> Path:
    export_dir = Path(conv["export_dir"])
    anexos_dir = out_dir / "anexos"
    md_path = out_dir / "conversa.md"

    lines = [
        f"# {PRODUCT_NAME} · Dossiê: {conv['chat_name']}",
        "",
        f"- Mensagens: {len(conv['messages'])} · plataforma {conv['platform']}",
    ]
    recorte = _recorte_md(conv)
    if recorte:
        lines.append(recorte)
    lines += [
        _resumo_midias(conv),
        f"- Objetivo da análise: {conv.get('objetivo') or '(não informado)'}",
        "",
    ]
    lines += _INSTRUCOES
    lines += _analise_md(conv.get("analise"))
    lines += ["## Conversa", ""]

    doc_count = 0
    fichas: list[tuple[Path, list[str]]] = []
    current_date = None
    for msg in conv["messages"]:
        if msg["date"] != current_date:
            current_date = msg["date"]
            lines += [f"### {current_date}", ""]
        if msg["is_system"]:
            lines.append(f"- _(sistema)_ {msg['text']}")
            continue
        head = f"- **{msg['time']} {msg['sender']}** (`{msg['id']}`)"
        lines.append(f"{head}: {msg['text']}" if msg["text"] else f"{head}:")
        for media in msg["media"]:
            name = media["filename"]
            if not media["present"]:
                lines.append(f"  - [{media['kind']} `{name}`: ausente da exportação]")
                continue
            if media["kind"] == "audio":
                if media.get("transcricao"):
                    lines.append(f"  - Áudio `{name}` — transcrição automática: “{media['transcricao']}”")
                else:
                    lines.append(f"  - Áudio `{name}` (sem transcrição)")
            elif media["kind"] == "pdf":
                doc_count += 1
                ficha_name = f"doc-{doc_count:03d}.md"
                lines.append(f"  - PDF `{name}` ({media.get('pages') or '?'} páginas) — "
                             f"ficha: anexos/{ficha_name}")
                fichas.append((anexos_dir / ficha_name, _ficha(conv, msg, media, export_dir)))
            else:
                lines.append(f"  - {media['kind'].capitalize()} `{name}`")
            if media.get("comentario"):
                lines.append(f"    - Comentário (IA): {media['comentario']}")
        for kind in msg.get("omitted") or []:
            lines.append(f"  - [{kind} citado na conversa, mas não veio na exportação]")
    lines.append("")

    for ficha_path, ficha_lines in fichas:
        ficha_path.parent.mkdir(parents=True, exist_ok=True)
        ficha_path.write_text("\n".join(ficha_lines), encoding="utf-8")

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def _ficha(conv: dict, msg: dict, media: dict, export_dir: Path) -> list[str]:
    name = media["filename"]
    lines = [
        f"# Ficha do documento: {name}",
        "",
        f"- Enviado por {msg['sender']} em {msg['date']} às {msg['time']} (mensagem `{msg['id']}`)",
        f"- Páginas: {media.get('pages') or '?'}",
        "",
    ]
    if media.get("comentario"):
        lines += ["## Comentário (IA, com contexto da conversa)", "", media["comentario"], ""]
    try:
        text, pages = _pdf_text(export_dir / media["path"])
    except Exception as e:
        text, pages = "", media.get("pages") or 0
        lines += [f"> Não foi possível extrair texto: {e}", ""]
    if text:
        shown = min(pages, _PDF_MAX_PAGES)
        lines += [f"## Texto extraído (primeiras {shown} de {pages} páginas)", "",
                  "```", text, "```", ""]
    elif pages:
        lines += ["> PDF sem texto extraível (provavelmente escaneado).", ""]
    return lines
