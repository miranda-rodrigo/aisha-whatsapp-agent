# ruff: noqa: E402
import asyncio
import copy
import unittest
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import configure_test_env

configure_test_env()
from aisha.chat_export import assets, enrich, handler, store
from aisha.chat_export.ingest import ExportError
from aisha.chat_export.pdf import template


def record():
    return {
        "version": 3,
        "revision": "a" * 32,
        "expires_at": "2099-01-01T00:00:00+00:00",
        "analysis": None,
        "comments": None,
        "status": "processing",
        "messages": [
            {
                "id": "msg-1",
                "sender": "Ana",
                "date": "14/11/2026",
                "time": "10:00",
                "text": "arquivo",
                "media": [
                    {
                        "kind": "audio",
                        "name": "fala.wav",
                        "number": 1,
                        "hash": "audio",
                        "suffix": ".wav",
                        "seconds": 1,
                        "status": "pending",
                    }
                ],
            },
            {
                "id": "msg-2",
                "sender": "Bia",
                "date": "14/11/2026",
                "time": "10:01",
                "text": "foto",
                "media": [
                    {
                        "kind": "image",
                        "name": "foto.png",
                        "number": 1,
                        "hash": "image",
                        "status": "pending",
                    }
                ],
            },
        ],
    }


class EnrichmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_partial_result_persistence_cache_and_cleanup(self):
        r = record()
        r["messages"].append(copy.deepcopy(r["messages"][0]))
        r["messages"][2]["id"] = "msg-3"
        files = {"audio": b"audio", "image": b"image"}
        with (
            patch.object(store, "current", AsyncMock(return_value=True)),
            patch.object(store, "update", AsyncMock()) as save,
            patch.object(
                enrich, "transcribe", AsyncMock(return_value="Confirmado às 14 horas.")
            ) as transcribe,
            patch.object(
                enrich, "describe_image", AsyncMock(side_effect=RuntimeError("failure"))
            ),
            patch.object(assets, "upload", AsyncMock(return_value="private.jpg")),
        ):
            result = await enrich.run("alice", r, files)
            self.assertFalse(files)
            self.assertEqual(
                result["messages"][0]["media"][0]["transcript"],
                "Confirmado às 14 horas.",
            )
            self.assertEqual(result["messages"][1]["media"][0]["status"], "failed")
            self.assertEqual(result["messages"][1]["media"][0]["object"], "private.jpg")
            self.assertEqual(transcribe.await_count, 1)
            self.assertGreaterEqual(save.await_count, 3)
            await enrich.run("alice", result, {"audio": b"audio"})
            self.assertEqual(transcribe.await_count, 1)

    async def test_deleted_conversation_does_not_publish_late_result(self):
        r = record()
        r["messages"] = r["messages"][:1]
        files = {"audio": b"audio"}
        with (
            patch.object(store, "current", AsyncMock(side_effect=[True, False])),
            patch.object(store, "update", AsyncMock()) as save,
            patch.object(enrich, "transcribe", AsyncMock(return_value="done")),
        ):
            with self.assertRaises(ExceptionGroup):
                await enrich.run("alice", r, files)
            save.assert_not_awaited()
            self.assertFalse(files)

    async def test_cancellation_clears_audio(self):
        r = record()
        r["messages"] = r["messages"][:1]
        files = {"audio": b"audio"}
        entered = asyncio.Event()

        async def slow(*args):
            entered.set()
            await asyncio.sleep(60)

        with (
            patch.object(store, "current", AsyncMock(return_value=True)),
            patch.object(enrich, "transcribe", slow),
        ):
            task = asyncio.create_task(enrich.run("alice", r, files))
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertFalse(files)

    async def test_context_overflow_is_not_silently_analyzed(self):
        with (
            patch.object(store, "update", AsyncMock()),
            patch.object(enrich, "MAX_CONTEXT", 1),
        ):
            with self.assertRaisesRegex(ExportError, "200 mil"):
                await enrich.run("alice", record(), {})

    async def test_storage_ownership_and_forget_failure(self):
        with self.assertRaises(ValueError):
            await assets.download(
                "alice",
                assets.owner("bob") + "/1-" + "a" * 32 + "/" + "b" * 64 + ".jpg",
            )
        with (
            patch.object(store, "forget", AsyncMock()) as delete,
            patch.object(
                assets, "remove_prefix", AsyncMock(side_effect=RuntimeError())
            ),
        ):
            with self.assertRaisesRegex(ExportError, "imagens"):
                await store.forget_with_assets("alice")
            delete.assert_awaited_once_with("alice")

    async def test_analysis_failure_still_delivers_sources_and_can_retry(self):
        r = record()
        r["comments"] = []
        with (
            patch.object(store, "load_record", AsyncMock(return_value=r)),
            patch.object(store, "current", AsyncMock(return_value=True)),
            patch.object(store, "save_analysis", AsyncMock()),
            patch.object(enrich, "hydrated", AsyncMock(return_value=r["messages"])),
            patch.object(
                handler, "analyze_structured", AsyncMock(side_effect=RuntimeError())
            ),
            patch.object(
                handler, "render_pdf", AsyncMock(return_value=b"%PDF")
            ) as render,
        ):
            send_file = AsyncMock()
            await handler.deliver_pdf("alice", AsyncMock(), send_file)
            self.assertTrue(render.call_args.args[1]["unavailable"])
            send_file.assert_awaited_once()

    def test_guides_figures_sources_and_invalid_comment(self):
        r = record()
        r["messages"][0]["media"][0].update(
            transcript="<script>conteúdo</script>", status="ready"
        )
        analysis = {
            "claims": [],
            "comments": [
                {"after_id": "msg-1", "text": "Não deve aparecer", "ids": ["inventado"]}
            ],
        }
        html = template(r["messages"], analysis, "Teste")
        for text in [
            "Como ler este relatório",
            "Instruções para uma IA",
            "Áudio 01",
            "Figura 01",
            "msg-1",
            "&lt;script&gt;",
        ]:
            self.assertIn(text, html)
        self.assertNotIn("Não deve aparecer", html)
        self.assertNotIn("<script>", html)

    async def test_transient_retry_is_bounded(self):
        import httpx
        from openai import APIConnectionError

        failure = APIConnectionError(
            request=httpx.Request(
                "POST", "https://api.openai.com/v1/audio/transcriptions"
            )
        )
        call = AsyncMock(side_effect=[failure, failure, "ok"])
        with patch.object(enrich.asyncio, "sleep", AsyncMock()):
            self.assertEqual(await enrich.retry(call), "ok")
        self.assertEqual(call.await_count, 3)

    async def test_cleanup_only_expired_owned_prefixes(self):
        root = "a" * 64

        async def listing(prefix):
            if not prefix:
                return [{"name": root}, {"name": "unrelated"}]
            return [{"name": "1-" + "b" * 32}, {"name": "9999999999-" + "c" * 32}]

        with (
            patch.object(assets, "entries", listing),
            patch.object(assets, "remove_prefix", AsyncMock()) as remove,
        ):
            await assets.cleanup()
            remove.assert_awaited_once_with(root + "/1-" + "b" * 32)

    async def test_subprocess_cancelled_before_temp_removal(self):
        import tempfile
        from pathlib import Path

        before = set(Path(tempfile.gettempdir()).glob("aisha-audio-*"))
        process = AsyncMock()
        process.returncode = None
        from unittest.mock import Mock

        process.kill = Mock()
        entered = asyncio.Event()

        async def waiting():
            entered.set()
            if process.kill.called:
                process.returncode = -9
                return
            await asyncio.sleep(60)

        process.wait.side_effect = waiting
        with patch.object(
            enrich.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)
        ):
            task = asyncio.create_task(enrich.transcribe(b"audio", ".wav", 1))
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        process.kill.assert_called_once()
        self.assertEqual(set(Path(tempfile.gettempdir()).glob("aisha-audio-*")), before)
