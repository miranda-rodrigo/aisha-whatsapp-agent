"""Retention and multi-audio lifecycle regressions, without network access."""

import asyncio
import copy
import unittest
from unittest.mock import AsyncMock, patch

from tests.aisha_unit.skills.test_export_enrich import record
from aisha.chat_export import enrich, handler, store


class AudioPocTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_audio_released_while_other_audio_is_running(self):
        r = record()
        r["messages"] = [r["messages"][0], copy.deepcopy(r["messages"][0])]
        r["messages"][1]["media"][0]["hash"] = "second"
        files = {"audio": b"first", "second": b"second"}
        waiting, release = asyncio.Event(), asyncio.Event()

        async def transcribe(raw, *args):
            if raw == b"second":
                waiting.set()
                await release.wait()
            return raw.decode()

        with (
            patch.object(store, "current", AsyncMock(return_value=True)),
            patch.object(store, "update", AsyncMock()),
            patch.object(enrich, "transcribe", transcribe),
        ):
            task = asyncio.create_task(enrich.run("poc", r, files))
            await waiting.wait()
            self.assertNotIn("audio", files)
            self.assertIn("second", files)
            release.set()
            result = await task
        self.assertFalse(files)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["messages"][1]["media"][0]["transcript"], "second")

    async def test_failed_audio_marks_partial_without_losing_other_transcripts(self):
        r = record()
        r["messages"] = [r["messages"][0], copy.deepcopy(r["messages"][0])]
        r["messages"][1]["media"][0]["hash"] = "bad"
        with (
            patch.object(store, "current", AsyncMock(return_value=True)),
            patch.object(store, "update", AsyncMock()),
            patch.object(
                enrich, "transcribe", AsyncMock(side_effect=["Olá", ValueError()])
            ),
        ):
            result = await enrich.run("poc", r, {"audio": b"ok", "bad": b"bad"})
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["messages"][0]["media"][0]["transcript"], "Olá")
        self.assertNotIn("transcript", result["messages"][1]["media"][0])

    async def test_forget_waits_for_active_job_cleanup(self):
        cleaned = asyncio.Event()
        started = asyncio.Event()

        async def job():
            try:
                started.set()
                await asyncio.sleep(60)
            finally:
                cleaned.set()

        task = asyncio.create_task(job())
        await started.wait()

        async def delete(phone):
            self.assertTrue(cleaned.is_set())

        handler._active_jobs["poc"] = task
        try:
            with patch.object(store, "forget_with_assets", delete):
                await handler.command("poc", "esquecer conversa", AsyncMock())
            self.assertTrue(task.cancelled())
        finally:
            handler._active_jobs.pop("poc", None)

    async def test_followup_expired_during_analysis_does_not_send_answer(self):
        send = AsyncMock()
        with (
            patch.object(handler, "enabled", return_value=True),
            patch.object(store, "load_record", AsyncMock(return_value=record())),
            patch.object(store, "current", AsyncMock(return_value=False)),
            patch.object(handler, "analyze", AsyncMock(return_value="PRIVATE ANSWER")),
        ):
            await handler.command("poc", "sobre a conversa: resumo", send)
        self.assertNotIn("PRIVATE ANSWER", str(send.call_args_list))
        self.assertIn("expirou", send.call_args.args[1])

    async def test_identical_upload_preserves_original_expiry(self):
        r = record()
        r["fingerprint"] = "same"
        with (
            patch.object(store, "load_record", AsyncMock(return_value=r)),
            patch.object(store, "save", AsyncMock()) as save,
        ):
            reused = await enrich.begin("poc", [], "same", "title", "")
        self.assertEqual(reused["expires_at"], r["expires_at"])
        save.assert_not_awaited()

    async def test_expired_record_cannot_be_updated_or_analyzed(self):
        r = record()
        r["expires_at"] = "2000-01-01T00:00:00+00:00"
        from aisha.chat_export.ingest import ExportError

        with patch.object(store, "get_client") as client:
            with self.assertRaises(ExportError):
                await store.update("poc", r)
            with self.assertRaises(ExportError):
                await store.save_analysis("poc", r, {})
            client.assert_not_called()

    async def test_image_storage_failure_does_not_abort_audio(self):
        from aisha.chat_export import assets

        with (
            patch.object(store, "current", AsyncMock(return_value=True)),
            patch.object(store, "update", AsyncMock()),
            patch.object(enrich, "transcribe", AsyncMock(return_value="Olá")),
            patch.object(enrich, "describe_image", AsyncMock(return_value="Foto")),
            patch.object(assets, "upload", AsyncMock(side_effect=RuntimeError())),
        ):
            result = await enrich.run("poc", record(), {"audio": b"a", "image": b"i"})
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["messages"][0]["media"][0]["transcript"], "Olá")
        self.assertTrue(result["messages"][1]["media"][0]["display_error"])
