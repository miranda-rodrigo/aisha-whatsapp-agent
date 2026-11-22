"""Synthetic PDF QA. --live uses real STT/vision/Supabase, never sends WhatsApp.

python -m scripts.check_export_media [--live] [--output /tmp/media-preview]
"""

import argparse
import asyncio
import base64
import io
import json
import os
import resource
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pymupdf
from PIL import Image, ImageDraw

from aisha import supabase_http
from aisha.chat_export import assets, handler, media, store
from aisha.chat_export.pdf import render_pdf


def fixture(audio_only=False):
    im = Image.new("RGB", (1200, 700), "#eef3f8")
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((100, 180, 1100, 470), radius=30, fill="#1d4e89")
    draw.rectangle((160, 450, 200, 610), fill="#8a6a32")
    draw.rectangle((1000, 450, 1040, 610), fill="#8a6a32")
    draw.line((1000, 510, 1040, 550), fill="white", width=14)
    out = io.BytesIO()
    im.save(out, "PNG")
    chat = """[14/11/2026, 10:00:00] Ana: A lateral da cama está quebrada. Gostaria de acionar a garantia.
[14/11/2026, 10:01:00] Ana: <attached: cama.png>
[14/11/2026, 10:02:00] Bruno: <attached: reuniao.mp3>
[14/11/2026, 10:03:00] Ana: Confirmado para amanhã às 14h.
[14/11/2026, 10:04:00] Bruno: <attached: manual.pdf>
[14/11/2026, 10:05:00] Ana: <attached: ausente.opus>
[14/11/2026, 10:06:00] Bruno: <attached: budget.mp3>
[14/11/2026, 10:07:00] Ana: <attached: address.mp3>
"""
    if audio_only:
        chat = "\n".join(line for line in chat.splitlines() if "cama.png" not in line)
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("_chat.txt", chat)
        archive.writestr("cama.png", out.getvalue())
        archive.writestr(
            "reuniao.mp3", Path("tests/fixtures/export_media/meeting.mp3").read_bytes()
        )
        for name in ("budget.mp3", "address.mp3"):
            archive.writestr(
                name, Path("tests/fixtures/export_media", name).read_bytes()
            )
        archive.writestr("manual.pdf", b"DOCUMENT MUST NOT BE READ")
    return zipped.getvalue()


async def main(live=False, output=None, audio_only=False):
    start = time.monotonic()
    before = {p for p in Path(tempfile.gettempdir()).glob("aisha-*") if p.is_dir()}
    data = fixture(audio_only)
    messages, files = await asyncio.to_thread(media.prepare, data)
    if not live:
        for message in messages:
            for item in message["media"]:
                if item["status"] == "pending":
                    item["status"] = "ready"
                    if item["kind"] == "audio":
                        item["transcript"] = {
                            "reuniao.mp3": "A reunião ficou marcada para amanhã às quatorze horas. Por favor, confirme o horário.",
                            "budget.mp3": "O orçamento aprovado é de mil e duzentos reais. O pagamento será feito na sexta-feira.",
                            "address.mp3": "A entrega será na Rua das Flores, número cento e vinte. Por favor, avise quando chegar.",
                        }[item["name"]]
                    else:
                        item["image_data"] = base64.b64encode(
                            files[item["hash"]]
                        ).decode()
                        item["description"] = (
                            "Ilustração de uma cama azul com uma marca branca em um dos apoios."
                        )
        analysis = {
            "claims": [
                {
                    "text": "Ana solicitou atendimento pela garantia.",
                    "ids": [messages[0]["id"]],
                }
            ],
            "comments": [
                {
                    "after_id": messages[1]["id"],
                    "text": "Ana enviou a imagem após relatar um defeito e solicitar a garantia. A imagem isolada não comprova a causa do dano.",
                    "ids": [messages[0]["id"], messages[1]["id"]],
                }
            ],
        }
        pdf_data = await render_pdf(
            messages, analysis, "Demonstração · conversa com mídias"
        )
    else:
        phone = "synthetic-media-" + uuid.uuid4().hex
        send, send_file = AsyncMock(), AsyncMock()

        def respond(request):
            if request.url.host == "graph.facebook.com":
                return httpx.Response(
                    200,
                    json={
                        "url": "https://synthetic.invalid/chat",
                        "file_size": len(data),
                    },
                )
            return httpx.Response(200, content=data)

        try:
            with patch.dict(
                os.environ,
                WHATSAPP_EXPORT_ENABLED="true",
                WHATSAPP_EXPORT_MEDIA_ENABLED="true",
            ):
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(respond)
                ) as client:
                    await handler.document(
                        phone,
                        {"id": "synthetic", "filename": "demonstracao.zip"},
                        client,
                        send,
                        set(),
                        send_file,
                    )
                assert send_file.await_count == 1, "PDF not delivered to simulated Meta"
                r = await store.load_record(phone)
                assert (
                    r["version"] == 3
                    and r["analysis"]["claims"]
                    and not r["analysis"].get("unavailable")
                )
                items = [i for m in r["messages"] for i in m.get("media", [])]
                audio_items = [
                    i for i in items if i["kind"] == "audio" and i.get("hash")
                ]
                assert len(audio_items) == 3, "Expected three distinct audio files"
                assert all(i.get("transcript") for i in audio_items), "STT failed"
                if not audio_only:
                    assert any(i.get("description") for i in items), "Vision failed"
                    assert r["comments_status"] == "ready", "Comment generation failed"
                    assert await store.load_record(phone + "-other") is None
                    path = next(i["object"] for i in items if i.get("object"))
                    async with httpx.AsyncClient() as client:
                        public = await client.get(
                            f"{assets.ROOT}/object/public/{assets.BUCKET}/{path}"
                        )
                        assert public.status_code != 200, (
                            "Private image publicly accessible"
                        )
                await supabase_http.aclose()
                with patch.object(
                    handler,
                    "analyze_structured",
                    AsyncMock(side_effect=AssertionError("Unexpected analysis")),
                ) as model:
                    await handler.command(phone, "reenviar pdf", send, send_file)
                    model.assert_not_awaited()
                assert send_file.await_count == 2
                assert (await store.load_record(phone))["expires_at"] == r["expires_at"]
                await handler.command(
                    phone,
                    "sobre a conversa: qual é o horário combinado?",
                    send,
                    send_file,
                )
                assert any(m["id"] in send.call_args.args[1] for m in r["messages"])
                pdf_data = send_file.call_args.args[1]
                messages = r["messages"]
                await store.forget_with_assets(phone)
                assert await store.load_record(phone) is None
                assert not await assets.entries(assets.owner(phone))
        finally:
            await store.forget_with_assets(phone)
            await supabase_http.aclose()
    doc = pymupdf.open(stream=pdf_data, filetype="pdf")
    text = "\n".join(p.get_text() for p in doc)
    for label in (
        "Como ler este relatório",
        "Instruções para uma IA",
        "Áudio 01",
        "manual.pdf",
        "Ausente da exportação",
    ):
        assert label in text, label
    assert all(m["id"] in text for m in messages)
    if not audio_only:
        assert "Figura 01" in text
        assert any(page.get_images() for page in doc)
    assert any(link.get("page", -1) >= 0 for p in doc for link in p.get_links())
    assert "DOCUMENT MUST NOT BE READ" not in text
    assert {
        p for p in Path(tempfile.gettempdir()).glob("aisha-*") if p.is_dir()
    } == before
    if output:
        path = Path(output)
        path.mkdir(parents=True, exist_ok=True)
        (path / "conversa-com-midias.pdf").write_bytes(pdf_data)
        (path / "conversa-com-tres-audios.zip").write_bytes(data)
        for n, page in enumerate(doc):
            page.get_pixmap().save(path / f"page-{n + 1}.png")
    print(
        json.dumps(
            {
                "media_smoke": "PASS",
                "live_services": live,
                "meta": "SIMULATED",
                "pages": len(doc),
                "bytes": len(pdf_data),
                "seconds": round(time.monotonic() - start, 2),
                "child_maxrss": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--audio-only", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    asyncio.run(main(args.live, args.output, args.audio_only))
