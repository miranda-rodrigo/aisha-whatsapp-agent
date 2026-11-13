"""Opt-in predeploy check: synthetic data, live Supabase/OpenAI, simulated Meta.

Run only with operator authorization: python -m scripts.check_export_live
No real WhatsApp messages are sent. The unique synthetic row is always deleted.
"""

import asyncio
import io
import json
import os
import uuid
import zipfile
from unittest.mock import AsyncMock, patch

import httpx
import pymupdf

from aisha import supabase_http
from aisha.chat_export import handler, store
from scripts.check_export_pdf import main as check_pdf


async def main():
    await check_pdf()
    phone = "synthetic-pdf-" + uuid.uuid4().hex
    other = phone + "-other"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "_chat.txt",
            "[13/11/2026, 10:00:00] Ana: A reunião será às 14h.\n[13/11/2026, 10:01:00] Bruno: Confirmado, às 14h.\n",
        )
    data = output.getvalue()

    def respond(request):
        if request.url.host == "graph.facebook.com":
            return httpx.Response(
                200,
                json={"url": "https://synthetic.invalid/chat", "file_size": len(data)},
            )
        return httpx.Response(200, content=data)

    send, send_file = AsyncMock(), AsyncMock()
    try:
        with patch.dict(os.environ, WHATSAPP_EXPORT_ENABLED="true"):
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(respond)
            ) as client:
                await handler.document(
                    phone,
                    {"id": "synthetic", "filename": "teste.zip"},
                    client,
                    send,
                    set(),
                    send_file,
                )
            send_file.assert_awaited_once()
            record = await store.load_record(phone)
            assert record["version"] == 2 and record["analysis"]["claims"]
            assert await store.load_record(other) is None
            pdf = pymupdf.open(stream=send_file.call_args.args[1], filetype="pdf")
            assert all(
                m["id"] in "".join(p.get_text() for p in pdf)
                for m in record["messages"]
            )
            await (
                supabase_http.aclose()
            )  # New connection, no in-memory conversation cache.
            with patch.object(
                handler,
                "analyze_structured",
                AsyncMock(side_effect=AssertionError("Unexpected model call")),
            ):
                await handler.command(phone, "reenviar pdf", send, send_file)
            assert send_file.await_count == 2
            assert (await store.load_record(phone))["expires_at"] == record[
                "expires_at"
            ]
            await handler.command(
                phone, "sobre a conversa: Qual o horário da reunião?", send, send_file
            )
            assert any(m["id"] in send.call_args.args[1] for m in record["messages"])
            await handler.command(phone, "esquecer conversa", send, send_file)
            assert await store.load_record(phone) is None
        print(
            json.dumps(
                {
                    "live_export_pdf": "PASS",
                    "storage": "PASS",
                    "analysis": "PASS",
                    "resend": "PASS",
                    "followup": "PASS",
                    "meta": "SIMULATED",
                }
            )
        )
    finally:
        await store.forget(phone)
        await supabase_http.aclose()


if __name__ == "__main__":
    asyncio.run(main())
