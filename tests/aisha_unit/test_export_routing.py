import unittest
from unittest.mock import AsyncMock, patch

import aisha.app as app
from tests.aisha_unit._helpers import configure_test_env  # noqa: F401


class ExportRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_zip_bypasses_pdf_pipeline(self):
        doc = {"id": "1", "filename": "chat.zip"}
        client = object()
        with (
            patch.object(app, "http_client", client, create=True),
            patch.object(app.export_handler, "document", AsyncMock()) as handle,
            patch.object(app, "extract_text_async", AsyncMock()) as extract,
        ):
            await app.handle_document("alice", {"document": doc})
            handle.assert_awaited_once_with(
                "alice",
                doc,
                client,
                app.send_message,
                app._processing,
                app.send_document,
            )
            extract.assert_not_awaited()

    async def test_followup_bypasses_general_agent(self):
        with (
            patch.object(
                app.export_handler, "command", AsyncMock(return_value=True)
            ) as command,
            patch("aisha.agent.run_agent", AsyncMock()) as agent,
        ):
            await app.handle_chat("export-test-user", "sobre a conversa: resumo")
            command.assert_awaited_once()
            agent.assert_not_awaited()
            self.assertNotIn("export-test-user", app._processing)

    async def test_document_upload_and_delivery_errors_propagate(self):
        import httpx

        for failure in ("/media", "/messages"):
            requests = []

            def respond(request):
                requests.append(request)
                return httpx.Response(
                    503 if request.url.path.endswith(failure) else 200,
                    json={"id": "synthetic-media"},
                )

            async with httpx.AsyncClient(
                transport=httpx.MockTransport(respond)
            ) as client:
                with patch.object(app, "http_client", client, create=True):
                    with self.assertRaises(httpx.HTTPStatusError):
                        await app.send_document(
                            "synthetic",
                            b"%PDF",
                            "conversa-analisada.pdf",
                            "application/pdf",
                        )
            self.assertEqual(len(requests), 1 if failure == "/media" else 2)
