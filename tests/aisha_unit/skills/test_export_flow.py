import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import httpx

from tests.aisha_unit._helpers import configure_test_env  # noqa: F401
from tests.aisha_unit.skills.test_export_ingest import make_zip, IOS
from aisha.chat_export import handler, store
from aisha.chat_export.ingest import ExportError, ingest_zip
from aisha.skills import pending_store


class StoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_roundtrip_isolation_replacement_expiry_delete(self):
        rows = {}

        def respond(request):
            if request.method == "POST":
                row = json.loads(request.content)
                rows[row["phone"]] = row
                return httpx.Response(201)
            self.assertEqual(request.url.params["kind"], "eq.wa_export")
            phone = request.url.params["phone"][3:]
            if request.method == "DELETE":
                rows.pop(phone, None)
                return httpx.Response(204)
            return httpx.Response(200, json=[rows[phone]] if phone in rows else [])

        messages = ingest_zip(make_zip({"_chat.txt": IOS}))
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with patch.object(store, "get_client", return_value=client):
                await store.save("alice", messages)
                self.assertEqual(await store.load("alice"), messages)
                self.assertIsNone(await store.load("bob"))
                expires = datetime.fromisoformat(rows["alice"]["expires_at"])
                self.assertAlmostEqual(
                    (expires - datetime.now(timezone.utc)).total_seconds(),
                    86400,
                    delta=3,
                )
                await store.save("alice", messages[:1])
                self.assertEqual(await store.load("alice"), messages[:1])
                rows["alice"]["expires_at"] = (
                    datetime.now(timezone.utc) - timedelta(seconds=1)
                ).isoformat()
                self.assertIsNone(await store.load("alice"))
                self.assertNotIn("alice", rows)
                await store.save("alice", messages)
                await store.forget("alice")
                self.assertIsNone(await store.load("alice"))

    async def test_storage_failures_are_explicit(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(503))
        ) as client:
            with patch.object(store, "get_client", return_value=client):
                for action in (
                    store.save("alice", []),
                    store.load("alice"),
                    store.forget("alice"),
                ):
                    with self.assertRaises(ExportError):
                        await action

    async def test_general_pending_cleanup_preserves_export(self):
        client = AsyncMock()
        with patch.object(pending_store, "get_client", return_value=client):
            await pending_store.clear_all_pending("alice")
        self.assertEqual(
            client.delete.call_args.kwargs["params"]["kind"], "neq.wa_export"
        )


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, WHATSAPP_EXPORT_ENABLED="true")
        self.env.start()
        self.addCleanup(self.env.stop)

    async def test_zip_flow_and_failure_preserves_previous(self):
        data = make_zip({"_chat.txt": IOS})

        def respond(request):
            if request.url.host == "graph.facebook.com":
                return httpx.Response(
                    200, json={"url": "https://media.test/chat", "file_size": len(data)}
                )
            return httpx.Response(200, content=data)

        send = AsyncMock()
        processing = set()
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with (
                patch.object(store, "save", AsyncMock()) as save,
                patch.object(handler, "deliver_pdf", AsyncMock()) as analyze,
            ):
                await handler.document(
                    "alice",
                    {"id": "1", "filename": "chat.zip"},
                    client,
                    send,
                    processing,
                )
                save.assert_awaited_once()
                analyze.assert_awaited_once_with("alice", send, None)
                self.assertFalse(processing)
                save.reset_mock()
                analyze.reset_mock()
                data = b"bad zip"
                await handler.document(
                    "alice",
                    {"id": "1", "filename": "chat.zip"},
                    client,
                    send,
                    processing,
                )
                save.assert_not_awaited()
                analyze.assert_not_awaited()
                data = make_zip({"_chat.txt": IOS})
                save.side_effect = ExportError("Falha ao salvar")
                await handler.document(
                    "alice",
                    {"id": "1", "filename": "chat.zip"},
                    client,
                    send,
                    processing,
                )
                analyze.assert_not_awaited()
                self.assertIn("Falha ao salvar", send.call_args.args[1])

    async def test_commands_and_feature_flag(self):
        send = AsyncMock()
        with (
            patch.object(
                store, "load", AsyncMock(return_value=[{"id": "test"}])
            ) as load,
            patch.object(
                handler, "analyze", AsyncMock(return_value="Resposta")
            ) as analyze,
        ):
            self.assertFalse(await handler.command("alice", "oi", send))
            self.assertTrue(
                await handler.command("alice", "Sobre a conversa: resumo", send)
            )
            load.assert_awaited_once_with("alice")
            analyze.assert_awaited_once_with([{"id": "test"}], "resumo")
            load.return_value = None
            await handler.command("alice", "sobre a conversa: resumo", send)
            self.assertIn("expirado", send.call_args.args[1])
        with (
            patch.dict(os.environ, WHATSAPP_EXPORT_ENABLED="false"),
            patch.object(store, "forget", AsyncMock()) as forget,
        ):
            await handler.command("alice", "esquecer conversa", send)
            forget.assert_awaited_once_with("alice")
            await handler.document("alice", {"filename": "chat.zip"}, None, send, set())
            self.assertIn("desativada", send.call_args.args[1])

    async def test_stream_download_limit_and_busy(self):
        def respond(request):
            if request.url.host == "graph.facebook.com":
                return httpx.Response(200, json={"url": "https://media.test/chat"})
            return httpx.Response(200, content=b"12345")

        send = AsyncMock()
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with (
                patch.object(handler, "MAX_ZIP_BYTES", 4),
                patch.object(store, "save", AsyncMock()) as save,
            ):
                await handler.document(
                    "alice", {"id": "1", "filename": "chat.zip"}, client, send, set()
                )
                save.assert_not_awaited()
                self.assertIn("excede", send.call_args.args[1])
        busy = {"alice"}
        await handler.document("alice", {"filename": "chat.zip"}, None, send, busy)
        self.assertEqual(busy, {"alice"})
        self.assertIn("anterior", send.call_args.args[1])
