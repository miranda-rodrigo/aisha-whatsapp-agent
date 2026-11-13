import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

from aisha.chat_export import handler, pdf, store
from aisha.chat_export.ingest import ExportError
from tests.aisha_unit._helpers import configure_test_env

configure_test_env()
MESSAGES = [
    dict(
        id="msg-a",
        date="13/11/2026",
        time="10:00",
        sender="Ana",
        text="Reunião às 14h 😊",
    ),
    dict(id="msg-b", date="13/11/2026", time="10:01", sender="Bia", text="Confirmado!"),
]
ANALYSIS = {
    "claims": [{"text": "A reunião foi confirmada.", "ids": ["msg-a", "msg-b"]}]
}
RECORD = {
    "version": 2,
    "messages": MESSAGES,
    "analysis": ANALYSIS,
    "title": "Conversa de teste",
    "expires_at": "2099-01-01T00:00:00+00:00",
}


class PdfTests(unittest.IsolatedAsyncioTestCase):
    def test_template_escapes_content_and_links(self):
        messages = [
            dict(MESSAGES[0], text='<script>fetch("https://evil.test")</script>')
        ]
        html = pdf.template(messages, {"claims": []}, "<img src=x>")
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img src=x>", html)
        self.assertIn("&lt;script&gt;", html)
        html = pdf.template(MESSAGES, ANALYSIS, "Teste")
        self.assertIn('href="#msg-a"', html)
        self.assertIn('id="msg-a"', html)

    async def test_size_timeout(self):
        with (
            patch.object(pdf, "_render", AsyncMock(return_value=b"12345")),
            patch.object(pdf, "MAX_PDF_BYTES", 4),
        ):
            with self.assertRaisesRegex(ExportError, "20 MB"):
                await pdf.render_pdf(MESSAGES, ANALYSIS, "Teste")

        async def slow(*args):
            await asyncio.sleep(1)

        with (
            patch.object(pdf, "_render", slow),
            patch.object(pdf, "RENDER_TIMEOUT", 0.01),
        ):
            with self.assertRaisesRegex(ExportError, "tempo"):
                await pdf.render_pdf(MESSAGES, ANALYSIS, "Teste")
        self.assertFalse(pdf._render_lock.locked())

    async def test_resend_reuses_analysis_even_after_delivery_failure(self):
        send = AsyncMock()
        send_file = AsyncMock(side_effect=RuntimeError("upload failed"))
        with (
            patch.object(store, "load_record", AsyncMock(return_value=RECORD)),
            patch.object(handler, "analyze_structured", AsyncMock()) as analyze,
            patch.object(handler, "render_pdf", AsyncMock(return_value=b"%PDF")),
        ):
            await handler.deliver_pdf("alice", send, send_file)
            self.assertIn("envio do PDF", send.call_args.args[1])
            send_file.side_effect = None
            with patch.dict(os.environ, WHATSAPP_EXPORT_ENABLED="true"):
                await handler.command("alice", "reenviar pdf", send, send_file)
            analyze.assert_not_awaited()
            send_file.assert_awaited_with(
                "alice", b"%PDF", "conversa-analisada.pdf", "application/pdf"
            )

    async def test_legacy_analyzes_and_persists_before_render(self):
        record = {k: v for k, v in RECORD.items() if k != "analysis"}
        record["version"] = 1
        with (
            patch.object(store, "load_record", AsyncMock(return_value=record)),
            patch.object(
                handler, "analyze_structured", AsyncMock(return_value=ANALYSIS)
            ) as analyze,
            patch.object(store, "save_analysis", AsyncMock()) as save,
            patch.object(
                handler, "render_pdf", AsyncMock(side_effect=RuntimeError("render"))
            ) as render,
        ):
            await handler.deliver_pdf("alice", AsyncMock(), AsyncMock())
            analyze.assert_awaited_once()
            save.assert_awaited_once_with("alice", record, ANALYSIS)
            render.assert_awaited_once()

    async def test_failed_persistence_does_not_render(self):
        record = {**RECORD, "analysis": None}
        with (
            patch.object(store, "load_record", AsyncMock(return_value=record)),
            patch.object(
                handler, "analyze_structured", AsyncMock(return_value=ANALYSIS)
            ),
            patch.object(
                store, "save_analysis", AsyncMock(side_effect=ExportError("save"))
            ),
            patch.object(handler, "render_pdf", AsyncMock()) as render,
        ):
            await handler.deliver_pdf("alice", AsyncMock(), AsyncMock())
            render.assert_not_awaited()

    async def test_legacy_record_upgrade_preserves_expiration_and_owner(self):
        import httpx

        record = {**RECORD, "version": 1}
        record.pop("analysis")
        requests = []

        def respond(request):
            requests.append(request)
            if request.method == "GET":
                return httpx.Response(
                    200, json=[{"payload": record, "expires_at": RECORD["expires_at"]}]
                )
            return httpx.Response(200, json=[{}])

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with patch.object(store, "get_client", return_value=client):
                loaded = await store.load_record("alice")
                await store.save_analysis("alice", loaded, ANALYSIS)
        import json

        request = requests[-1]
        self.assertEqual(request.url.params["phone"], "eq.alice")
        self.assertEqual(request.url.params["expires_at"], "eq." + RECORD["expires_at"])
        body = json.loads(request.content)
        self.assertEqual(set(body), {"payload"})
        self.assertEqual(body["payload"]["version"], 2)
        self.assertEqual(body["payload"]["analysis"], ANALYSIS)

    async def test_renderer_serializes_requests(self):
        active = 0
        peak = 0

        async def render(*args):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return b"pdf"

        with patch.object(pdf, "_render", render):
            await asyncio.gather(
                *(pdf.render_pdf(MESSAGES, ANALYSIS, "Teste") for _ in range(3))
            )
        self.assertEqual(peak, 1)
