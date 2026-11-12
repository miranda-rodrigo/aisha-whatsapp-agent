import unittest
from unittest.mock import AsyncMock, patch
from tests.aisha_unit._helpers import configure_test_env  # noqa: F401
import aisha.app as app


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
                "alice", doc, client, app.send_message, app._processing
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
