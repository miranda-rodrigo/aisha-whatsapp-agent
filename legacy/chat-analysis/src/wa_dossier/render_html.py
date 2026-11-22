"""Página única da conversa. Funciona em qualquer nível: camadas ausentes ficam ocultas."""

from __future__ import annotations

import html
import os
from pathlib import Path
from urllib.parse import quote

from .config import PRODUCT_NAME

CSS = """
:root {
  --desk: #1b2430;
  --paper: #f2f5f8;
  --sheet: #ffffff;
  --ink: #1c2430;
  --muted: #5c6b7a;
  --line: #d5dee8;
  --them: #ffffff;
  --me: #1d4e89;
  --me-ink: #f4f7fb;
  --brass: #8a6a32;
  --note: #eef3e6;
  --note-ink: #2c3b24;
  --warn: #f6e8e2;
  --warn-ink: #6e3428;
  --shadow: 0 18px 50px rgba(0, 0, 0, .28);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--desk);
  color: var(--ink);
  font-family: "Sora", "Avenir Next", "Segoe UI", sans-serif;
  line-height: 1.45;
}
.bar {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  background: rgba(27, 36, 48, .94);
  color: #e7eef6;
  border-bottom: 1px solid rgba(255, 255, 255, .08);
  backdrop-filter: blur(8px);
}
.brand {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  letter-spacing: .06em;
  color: #d7b56d;
}
.bar h1 { font-size: 15px; font-weight: 600; margin: 0; letter-spacing: -.01em; }
.bar p { margin: 2px 0 0; color: #a9b8c9; font-size: 12px; }
.toggles { display: flex; flex-wrap: wrap; gap: 8px; }
.toggles label {
  display: flex;
  gap: 6px;
  align-items: center;
  border: 1px solid rgba(255, 255, 255, .18);
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}
.toggles input { accent-color: #d7b56d; }
.toggles label.off { opacity: .45; cursor: not-allowed; }
.toggles small { font-weight: 400; opacity: .75; }
.sheet {
  width: min(820px, calc(100% - 28px));
  margin: 22px auto 48px;
  background: var(--paper);
  border-radius: 18px;
  box-shadow: var(--shadow);
  padding: 22px 18px 36px;
}
.analise { display: none; margin-bottom: 22px; }
body.show-analise .analise { display: block; }
.analise h2 { font-size: 18px; margin: 0 0 8px; }
.analise h3 { font-size: 13px; letter-spacing: .04em; text-transform: uppercase; color: var(--muted); margin: 16px 0 6px; }
.analise li { margin: 6px 0; }
.analise a, .stamp {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px;
  color: var(--brass);
  text-decoration: none;
}
.day {
  text-align: center;
  margin: 18px 0 10px;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: .04em;
}
.msg { display: flex; margin: 8px 0; }
.msg.me { justify-content: flex-end; }
.bubble {
  max-width: min(78%, 560px);
  background: var(--them);
  border: 1px solid var(--line);
  border-radius: 14px 14px 14px 4px;
  padding: 8px 10px 7px;
}
.msg.me .bubble {
  background: var(--me);
  color: var(--me-ink);
  border-color: transparent;
  border-radius: 14px 14px 4px 14px;
}
.who { font-size: 12px; font-weight: 600; margin-bottom: 2px; }
.msg.me .who { color: #d5e4f5; }
.time { float: right; margin-left: 10px; color: var(--muted); font-size: 11px; }
.msg.me .time { color: #c5d6ea; }
.text { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 14.5px; }
.media { margin-top: 8px; }
.media img, .media video {
  display: block;
  max-width: 100%;
  max-height: 360px;
  border-radius: 10px;
  background: #0e141c;
}
.media audio { width: min(100%, 280px); }
.file a { color: inherit; }
.omitted, .tx, .note {
  margin-top: 8px;
  border-radius: 8px;
  padding: 7px 8px;
  font-size: 13px;
}
.omitted { background: var(--warn); color: var(--warn-ink); }
.tx, .note { background: var(--note); color: var(--note-ink); }
.msg.me .tx, .msg.me .note { background: rgba(255, 255, 255, .12); color: var(--me-ink); }
.tx { display: none; white-space: pre-wrap; }
.note { display: none; }
body.show-tx .tx { display: block; }
body.show-note .note { display: block; }
.kicker { font-size: 10px; letter-spacing: .06em; text-transform: uppercase; opacity: .7; }
.stamp { display: inline-block; margin-top: 6px; }
.msg.me .stamp { color: #e4c98a; }
.system { text-align: center; color: var(--muted); font-size: 12px; margin: 10px 20px; }
.guide {
  margin-bottom: 18px;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 13px;
}
.guide summary { cursor: pointer; font-weight: 600; }
.guide ul { margin: 8px 0 2px; padding-left: 18px; }
.guide li { margin: 4px 0; }
.ai-warn { font-size: 12px; color: var(--warn-ink); background: var(--warn); border-radius: 8px; padding: 6px 8px; }
@media (max-width: 640px) {
  .bubble { max-width: 92%; }
  .sheet { width: calc(100% - 12px); padding: 14px 10px 24px; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
}
"""


def _src(html_path: Path, export_dir: Path, rel: str) -> str:
    target = (export_dir / rel).resolve()
    relative = Path(os.path.relpath(target, html_path.parent.resolve()))
    return quote(relative.as_posix(), safe="/")


def _bubble(msg: dict, html_path: Path, export_dir: Path, me: str | None) -> str:
    if msg["is_system"]:
        return f'<p class="system">{html.escape(msg["text"])}</p>'
    mine = bool(me) and msg["sender"].casefold() == me.casefold()
    who = html.escape(msg["sender"] or "")
    text = html.escape(msg["text"] or "")
    bits = [
        f'<article class="msg{" me" if mine else ""}" id="{html.escape(msg["id"])}">',
        '<div class="bubble">',
        f'<div class="who">{who}<span class="time">{html.escape(msg["time"])}</span></div>',
    ]
    if text:
        bits.append(f'<div class="text">{text}</div>')
    for media in msg["media"]:
        bits.append(_media_block(media, html_path, export_dir))
    for kind in msg.get("omitted") or []:
        bits.append(f'<div class="omitted">{html.escape(kind)} não veio na exportação</div>')
    bits.append(f'<a class="stamp" href="#{html.escape(msg["id"])}">{html.escape(msg["id"])}</a>')
    bits.append("</div></article>")
    return "\n".join(bits)


def _media_block(media: dict, html_path: Path, export_dir: Path) -> str:
    kind = media["kind"]
    name = html.escape(media.get("filename") or kind)
    if not media.get("present") or not media.get("path"):
        return f'<div class="omitted">{name}: arquivo ausente</div>'
    src = _src(html_path, export_dir, media["path"])
    chunks = ['<div class="media">']
    if kind in ("image", "sticker"):
        chunks.append(f'<img src="{src}" alt="{name}">')
    elif kind == "audio":
        chunks.append(f'<audio controls preload="none" src="{src}"></audio>')
    elif kind == "video":
        chunks.append(f'<video controls preload="metadata" src="{src}"></video>')
    elif kind == "pdf":
        pages = media.get("pages")
        label = f"{name}" + (f" · {pages} páginas" if pages else "")
        chunks.append(f'<div class="file"><a href="{src}">{html.escape(label)}</a></div>')
    else:
        chunks.append(f'<div class="file"><a href="{src}">{name}</a></div>')
    if media.get("transcricao"):
        chunks.append('<div class="tx"><div class="kicker">Transcrição automática</div>'
                      + html.escape(media["transcricao"]) + "</div>")
    elif media.get("transcricao_erro"):
        chunks.append('<div class="omitted">Transcrição falhou: '
                      + html.escape(media["transcricao_erro"]) + "</div>")
    if media.get("comentario"):
        chunks.append('<div class="note"><div class="kicker">Comentário (IA)</div>'
                      + html.escape(media["comentario"]) + "</div>")
    chunks.append("</div>")
    return "\n".join(chunks)


def _analise(analise: dict | None) -> str:
    if not analise:
        return ""
    parts = ['<section class="analise">', "<h2>Análise</h2>",
             '<p class="ai-warn">Gerada por IA a partir da conversa. Pode conter erros ou '
             'omissões: confira cada item nas mensagens citadas antes de usar.</p>',
             f'<p>{html.escape(analise.get("resumo") or "")}</p>']
    titles = {
        "linha_do_tempo": "Linha do tempo",
        "valores": "Valores",
        "compromissos": "Compromissos",
        "pendencias": "Pendências",
    }
    for key, title in titles.items():
        items = analise.get(key) or []
        if not items:
            continue
        parts.append(f"<h3>{title}</h3><ul>")
        for item in items:
            cites = " ".join(
                f'<a href="#{html.escape(mid)}">{html.escape(mid)}</a>'
                for mid in item.get("mensagens") or []
            )
            parts.append(f"<li>{html.escape(item.get('texto') or '')} {cites}</li>")
        parts.append("</ul>")
    for aviso in analise.get("avisos") or []:
        parts.append(f'<p class="omitted">{html.escape(aviso)}</p>')
    parts.append("</section>")
    return "\n".join(parts)


_GUIDE = """<details class="guide">
<summary>Como ler este documento</summary>
<ul>
<li>A conversa vem da exportação nativa do WhatsApp, em ordem cronológica. Fotos, áudios, vídeos e PDFs aparecem na mensagem em que foram enviados.</li>
<li>Cada mensagem tem um código (<span class="stamp">msg-…</span>). Clique nele para obter o link direto; use-o para citar a mensagem.</li>
<li><b>Transcrição automática</b>: texto literal do áudio, sem edição. Pode errar nomes e números; o áudio original prevalece.</li>
<li><b>Comentário (IA)</b> e <b>Análise</b>: interpretações geradas por IA. Confira nas mensagens citadas antes de usar.</li>
<li>Os botões no topo ligam e desligam cada camada. Para perguntar a uma IA sobre a conversa, use o arquivo <code>conversa.md</code>, que traz instruções de resposta.</li>
</ul>
</details>"""


def _contagem(conv: dict, n_msg: int) -> str:
    recorte = conv.get("recorte") or {}
    total = recorte.get("mensagens_total")
    if total and recorte.get("desde"):
        return (f"{n_msg} de {total} mensagens, desde {html.escape(recorte['desde'])}")
    return f"{n_msg} mensagens"


def render_html(conv: dict, html_path: Path, me: str | None = None) -> Path:
    html_path.parent.mkdir(parents=True, exist_ok=True)
    export_dir = Path(conv["export_dir"])
    n_msg = len(conv["messages"])
    n_audio = sum(1 for m in conv["messages"] for media in m["media"] if media["kind"] == "audio")
    has_tx = any(media.get("transcricao") for m in conv["messages"] for media in m["media"])
    has_note = any(media.get("comentario") for m in conv["messages"] for media in m["media"])
    has_an = bool(conv.get("analise"))
    classes = []
    if has_tx:
        classes.append("show-tx")
    if has_note:
        classes.append("show-note")
    if has_an:
        classes.append("show-analise")

    def toggle(layer: str, label: str, available: bool) -> str:
        if not available:
            return (f'<label class="off" title="Esta camada ainda não foi gerada. '
                    f'Rode o build com um nível maior.">'
                    f'<input type="checkbox" disabled> {label} <small>— ainda não gerado</small></label>')
        return f'<label><input type="checkbox" data-layer="{layer}" checked> {label}</label>'

    body = [_GUIDE, _analise(conv.get("analise"))]
    current = None
    for msg in conv["messages"]:
        if msg["date"] != current:
            current = msg["date"]
            body.append(f'<div class="day">{html.escape(current or "")}</div>')
        body.append(_bubble(msg, html_path, export_dir, me))

    page = f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(conv["chat_name"])} · {PRODUCT_NAME}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Sora:wght@400;500;600&display=swap">
<style>{CSS}</style>
</head>
<body class="{" ".join(classes)}">
<header class="bar">
  <div>
    <div class="brand">{PRODUCT_NAME}</div>
    <h1>{html.escape(conv["chat_name"])}</h1>
    <p>{_contagem(conv, n_msg)} · {n_audio} áudios · nível {conv.get("nivel", 0)}</p>
  </div>
  <div class="toggles">
    {toggle("show-tx", "Transcrições", has_tx)}
    {toggle("show-note", "Comentários", has_note)}
    {toggle("show-analise", "Análise", has_an)}
  </div>
</header>
<main class="sheet">
{"".join(body)}
</main>
<script>
document.querySelectorAll(".toggles input").forEach(function (box) {{
  box.addEventListener("change", function () {{
    document.body.classList.toggle(box.dataset.layer, box.checked);
  }});
}});
</script>
</body>
</html>
"""
    html_path.write_text(page, encoding="utf-8")
    return html_path
