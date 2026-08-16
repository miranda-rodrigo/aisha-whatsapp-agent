import unittest
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import configure_test_env

configure_test_env()

from aisha.skills import raw_transcription_state as state


class RawTranscriptionStateTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _close(coro):
        coro.close()

    def setUp(self):
        state._store.clear()

    def tearDown(self):
        state._store.clear()

    def test_store_get_and_pop_in_memory(self):
        with patch.object(state, "_schedule", side_effect=self._close) as schedule:
            state.store_raw_transcription("5511", "texto")
            self.assertEqual(state.get_raw_transcription("5511"), "texto")
            self.assertEqual(state.pop_raw_transcription("5511"), "texto")
            self.assertIsNone(state.get_raw_transcription("5511"))

        self.assertEqual(schedule.call_count, 2)

    def test_expired_entry_is_evicted(self):
        state._store["5511"] = state._Entry("antigo", ts=100)
        with patch.object(state.time, "time", return_value=100 + state._TTL_SECONDS + 1), patch.object(
            state, "_schedule", side_effect=self._close
        ) as schedule:
            self.assertIsNone(state.get_raw_transcription("5511"))

        schedule.assert_called_once()

    async def test_async_get_restores_persistent_value(self):
        with patch.object(
            state, "get_pending", AsyncMock(return_value={"payload": {"raw_text": "restaurado"}})
        ):
            self.assertEqual(await state.get_raw_transcription_async("5511"), "restaurado")
            self.assertEqual(state.get_raw_transcription("5511"), "restaurado")

    async def test_async_get_handles_empty_payload(self):
        with patch.object(state, "get_pending", AsyncMock(return_value={"payload": {}})):
            self.assertIsNone(await state.get_raw_transcription_async("5511"))

    async def test_async_pop_falls_back_to_persistence_and_clears_it(self):
        with (
            patch.object(state, "_schedule", side_effect=self._close),
            patch.object(
                state, "get_pending", AsyncMock(return_value={"payload": {"raw_text": "persistido"}})
            ),
            patch.object(state, "clear_pending", AsyncMock()) as clear,
        ):
            self.assertEqual(await state.pop_raw_transcription_async("5511"), "persistido")

        clear.assert_awaited_once_with("5511", "transcription")
