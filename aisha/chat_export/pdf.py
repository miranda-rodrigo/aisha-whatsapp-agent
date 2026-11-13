"""Private print template inspired by wa_dossier/render_html.py; no remote assets."""

import asyncio
import base64
import html
import tempfile
from pathlib import Path

from .analysis import validate_analysis
from .ingest import ExportError
from .parser import parse_chat

MAX_PDF_BYTES = 20 * 1024 * 1024
RENDER_TIMEOUT = 60
_render_lock = asyncio.Semaphore(1)
FONT_DIR = Path(__file__).with_name("fonts")


def template(messages: list[dict], analysis: dict, title: str) -> str:
    esc = html.escape
    fonts = "".join(
        f"@font-face{{font-family:{family};src:url(data:font/ttf;base64,{base64.b64encode((FONT_DIR / filename).read_bytes()).decode()}) format('truetype');font-weight:{weight};}}"
        for family, filename, weight in [
            ("Sora", "Sora.ttf", "100 900"),
            ("Mono", "Mono.ttf", "400"),
            ("Emoji", "Emoji.ttf", "100 900"),
        ]
    )
    participants = list(
        dict.fromkeys(m["sender"] for m in messages if m["sender"] != "[sistema]")
    )
    mine = participants[0] if participants else None
    claims = validate_analysis(analysis, messages)["claims"]
    summary = "".join(
        "<li>"
        + esc(c["text"])
        + '<div class="refs">'
        + " · ".join(f'<a href="#{esc(mid)}">{esc(mid)}</a>' for mid in c["ids"])
        + "</div></li>"
        for c in claims
    )
    if not summary:
        summary = "<li>Não foram encontradas conclusões com referências válidas.</li>"
    parts = []
    day = None
    for m in messages:
        if m["date"] != day:
            day = m["date"]
            parts.append(f'<h3 class="day">{esc(day)}</h3>')
        system = m["sender"] == "[sistema]"
        klass = (
            "system" if system else ("bubble mine" if m["sender"] == mine else "bubble")
        )
        # Recover media markers for v1 records without rewriting original text.
        parsed = parse_chat(f"[{m['date']}, {m['time']}] {m['sender']}: {m['text']}")
        marker = bool(
            parsed.messages
            and (parsed.messages[0].attachments or parsed.messages[0].omitted_media)
        )
        marker = (
            marker or "(file attached)" in m["text"] or "(arquivo anexado)" in m["text"]
        )
        note = (
            '<div class="media">Mídia não processada nesta versão.</div>'
            if marker
            else ""
        )
        parts.append(
            f'<article class="{klass}" id="{esc(m["id"])}"><div class="who">{esc(m["sender"])} <span class="time">{esc(m["date"])} · {esc(m["time"])}</span></div><div class="text">{esc(m["text"])}</div>{note}<div class="stamp">{esc(m["id"])}</div></article>'
        )
    period = (
        f"{messages[0]['date']} a {messages[-1]['date']}"
        if messages
        else "Sem mensagens"
    )
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
{fonts}
@page {{ size:A4; margin:16mm 14mm 18mm; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; color:#1c2430; font:10pt Sora,Emoji,sans-serif; line-height:1.55; -webkit-print-color-adjust:exact; }}
header {{ background:#1b2430; color:#f4f7fb; padding:20px; border-radius:12px; }}
.brand {{ color:#d7b56d; font:9pt Mono,monospace; letter-spacing:1px; }}
h1 {{ font-size:19pt; margin:8px 0; overflow-wrap:anywhere; }}
.meta {{ font-size:9pt; color:#d5e4f5; overflow-wrap:anywhere; }}
.guide {{ background:#f2f5f8; padding:12px; margin:14px 0; border-radius:8px; font-size:8pt; }}
h2 {{ font-size:15pt; color:#1d4e89; break-after:avoid; }}
.analysis {{ background:#eef3e6; padding:14px 20px; border-radius:10px; }}
.analysis li {{ margin:10px 0; break-inside:avoid; }}
a,.refs,.stamp {{ font:7.5pt Mono,monospace; color:#8a6a32; overflow-wrap:anywhere; }}
.refs {{ margin-top:5px; }}
.timeline {{ break-before:page; }}
.day {{ text-align:center; font-size:9pt; color:#5c6b7a; margin:18px 0 10px; break-after:avoid; }}
.bubble {{ width:80%; background:#f2f5f8; border:1px solid #d5dee8; border-radius:12px 12px 12px 3px; padding:10px 12px; margin:9px 0; box-decoration-break:clone; -webkit-box-decoration-break:clone; }}
.mine {{ margin-left:auto; background:#1d4e89; color:#f4f7fb; border-color:#1d4e89; border-radius:12px 12px 3px 12px; }}
.who {{ font-size:8pt; font-weight:600; break-after:avoid; }}
.time {{ font-weight:400; font-size:7pt; opacity:.8; }}
.text {{ white-space:pre-wrap; overflow-wrap:anywhere; orphans:3; widows:3; }}
.stamp {{ margin-top:7px; break-before:avoid; }}
.mine .stamp {{ color:#e4c98a; }}
.media {{ font-size:8pt; background:#f6e8e2; color:#6e3428; padding:5px; margin-top:5px; }}
.system {{ color:#5c6b7a; font-size:8pt; padding:10px; text-align:center; }}
</style></head><body><header><div class="brand">AISHA · CONVERSA ANALISADA</div><h1>{esc(title)}</h1><div class="meta">{esc(period)} · {len(messages)} mensagens<br>{esc(" · ".join(participants))}</div></header>
<div class="guide"><b>Análise somente do texto.</b> Áudios, imagens e PDFs não foram processados. Balões azuis representam o primeiro participante, não necessariamente quem enviou o ZIP à Aisha. Referências apontam às mensagens originais. A interpretação da IA pode conter erros; confira as fontes.</div>
<h2>Análise · interpretação da IA</h2><section class="analysis"><ul>{summary}</ul></section>
<section class="timeline"><h2>Conversa · mensagens originais</h2>{"".join(parts)}</section></body></html>"""


async def _render(source: str) -> bytes:
    from playwright.async_api import async_playwright

    # Chromium and all its artifacts are scoped to this request.
    with tempfile.TemporaryDirectory(prefix="aisha-pdf-") as directory:
        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                directory,
                headless=True,
                java_script_enabled=False,
                service_workers="block",
                accept_downloads=False,
                args=["--disable-background-networking"],
            )
            try:

                async def local_document(route):
                    if (
                        route.request.url == "https://aisha.invalid/print"
                        and route.request.is_navigation_request()
                    ):
                        await route.fulfill(
                            status=200, content_type="text/html", body=source
                        )
                    else:
                        await route.abort()

                await context.route("**/*", local_document)
                page = await context.new_page()
                await page.goto("https://aisha.invalid/print", wait_until="load")
                await page.emulate_media(media="print")
                # Evaluation is our own fixed expression; imported scripts are disabled.
                await page.evaluate("document.fonts.ready")
                return await page.pdf(
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                    display_header_footer=True,
                    header_template="<span></span>",
                    footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#5c6b7a">Aisha · <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
                    tagged=True,
                    outline=True,
                )
            finally:
                await context.close()


async def render_pdf(messages: list[dict], analysis: dict, title: str) -> bytes:
    try:
        async with asyncio.timeout(RENDER_TIMEOUT):
            async with _render_lock:
                result = await _render(template(messages, analysis, title))
    except TimeoutError as exc:
        raise ExportError(
            "O PDF excedeu o tempo de geração. Tente reenviar pdf."
        ) from exc
    if len(result) > MAX_PDF_BYTES:
        raise ExportError("O PDF excede 20 MB. Exporte um período menor.")
    return result
