import base64
import unittest
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import configure_test_env

configure_test_env()

from aisha.skills import image_state


class ImageStateTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _close(coro):
        coro.close()

    def setUp(self):
        image_state._pending.clear()

    def tearDown(self):
        image_state._pending.clear()

    def test_store_get_and_clear_in_memory(self):
        with patch.object(image_state, "_schedule", side_effect=self._close) as schedule:
            image_state.store_pending_image("5511", b"image", "image/png")
            entry = image_state.get_pending_image("5511")
            image_state.clear_pending_image("5511")

        self.assertEqual((entry.image_bytes, entry.mime_type), (b"image", "image/png"))
        self.assertIsNone(image_state.get_pending_image("5511"))
        self.assertEqual(schedule.call_count, 2)

    def test_expired_image_is_removed(self):
        image_state._pending["5511"] = image_state.PendingImage(b"x", "image/png", 10)
        with patch.object(
            image_state.time,
            "monotonic",
            return_value=10 + image_state.IMAGE_PENDING_TTL + 1,
        ), patch.object(image_state, "_schedule", side_effect=self._close) as schedule:
            self.assertIsNone(image_state.get_pending_image("5511"))

        schedule.assert_called_once()

    async def test_async_get_restores_image_with_default_mime(self):
        row = {"blob_b64": base64.b64encode(b"restored").decode(), "payload": {}}
        with patch.object(image_state, "get_pending", AsyncMock(return_value=row)):
            entry = await image_state.get_pending_image_async("5511")

        self.assertEqual(entry.image_bytes, b"restored")
        self.assertEqual(entry.mime_type, "image/jpeg")
        self.assertIs(image_state._pending["5511"], entry)

    async def test_async_get_returns_none_without_blob(self):
        with patch.object(image_state, "get_pending", AsyncMock(return_value={"payload": {}})):
            self.assertIsNone(await image_state.get_pending_image_async("5511"))
