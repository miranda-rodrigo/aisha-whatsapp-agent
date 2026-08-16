import base64
import unittest
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import configure_test_env

configure_test_env()

from aisha.skills import document_state


class DocumentStateTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _close(coro):
        coro.close()

    def setUp(self):
        document_state._pending.clear()

    def tearDown(self):
        document_state._pending.clear()

    def test_store_get_and_clear_in_memory(self):
        with patch.object(document_state, "_schedule", side_effect=self._close) as schedule:
            document_state.store_pending_document("5511", b"pdf", 3, "legenda")
            entry = document_state.get_pending_document("5511")
            document_state.clear_pending_document("5511")

        self.assertEqual(
            (entry.pdf_bytes, entry.total_pages, entry.caption),
            (b"pdf", 3, "legenda"),
        )
        self.assertIsNone(document_state.get_pending_document("5511"))
        self.assertEqual(schedule.call_count, 2)

    def test_expired_document_is_removed(self):
        document_state._pending["5511"] = document_state.PendingDocument(b"x", 1, None, 10)
        with patch.object(
            document_state.time,
            "monotonic",
            return_value=10 + document_state.DOCUMENT_PENDING_TTL + 1,
        ), patch.object(document_state, "_schedule", side_effect=self._close) as schedule:
            self.assertIsNone(document_state.get_pending_document("5511"))

        schedule.assert_called_once()

    async def test_async_get_restores_document_and_defaults_missing_pages(self):
        row = {"blob_b64": base64.b64encode(b"restored").decode(), "payload": {"caption": "c"}}
        with patch.object(document_state, "get_pending", AsyncMock(return_value=row)):
            entry = await document_state.get_pending_document_async("5511")

        self.assertEqual(entry.pdf_bytes, b"restored")
        self.assertEqual(entry.total_pages, 0)
        self.assertEqual(entry.caption, "c")
        self.assertIs(document_state._pending["5511"], entry)

    async def test_async_get_returns_none_for_empty_persistence(self):
        with patch.object(document_state, "get_pending", AsyncMock(return_value=None)):
            self.assertIsNone(await document_state.get_pending_document_async("5511"))
