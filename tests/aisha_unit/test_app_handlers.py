"""Testes das decisões principais de chat, áudio, pendências e fuso."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from tests.aisha_unit._helpers import http_response, namespace

import aisha.app as app
import aisha.skills.document_state as document_state
import aisha.skills.image_state as image_state
import aisha.skills.webpage as webpage
import aisha.skills.youtube as youtube


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._clear_globals()

    def tearDown(self):
        self._clear_globals()

    @staticmethod
    def _clear_globals():
        app._processed_messages.clear()
        app._last_reply_time.clear()
        app._processing.clear()
        app._pending_timezone.clear()
        image_state._pending.clear()
        document_state._pending.clear()
        youtube._pending.clear()
        webpage._pending.clear()

    async def test_handle_chat_respects_per_user_lock(self):
        app._processing.add("5511")

        with patch.object(app, "send_message", AsyncMock()) as send:
            await app.handle_chat("5511", "segunda mensagem")

        send.assert_awaited_once()
        self.assertIn("Ainda estou processando", send.await_args.args[1])
        self.assertIn("5511", app._processing)

    async def test_handle_chat_uses_fast_path_delivers_and_releases_lock(self):
        result = namespace(
            response_id="response-1",
            image_bytes=b"image",
            text="resposta",
            tools_called=["web_search"],
        )

        with (
            patch.object(app, "_is_retroactive_transcription_request", return_value=False),
            patch.object(app, "extract_youtube_url", return_value=None),
            patch.object(app, "_hydrate_pendings", AsyncMock()),
            patch.object(app, "_get_pending_description", return_value=None),
            patch.object(app, "wants_new_session", return_value=False),
            patch.object(app, "is_trivial_message", return_value=True),
            patch.object(app, "get_response_id", AsyncMock(return_value="previous")),
            patch("aisha.agent.run_fast_path", AsyncMock(return_value=result)) as fast,
            patch.object(app, "upsert_session", AsyncMock()) as upsert,
            patch.object(app, "send_image", AsyncMock()) as send_image,
            patch.object(app, "send_message", AsyncMock()) as send,
            patch.object(app, "increment_stat", AsyncMock()) as increment,
        ):
            await app.handle_chat("5511", "oi")

        fast.assert_awaited_once_with(
            "oi",
            previous_response_id="previous",
            phone="5511",
        )
        upsert.assert_awaited_once_with("5511", "response-1")
        send_image.assert_awaited_once_with("5511", b"image")
        self.assertIn(unittest.mock.call("5511", "resposta"), send.await_args_list)
        increment.assert_awaited_once_with("5511", "tool_web_search")
        self.assertNotIn("5511", app._processing)

    async def test_handle_chat_cancels_pending_state(self):
        with (
            patch.object(app, "_is_retroactive_transcription_request", return_value=False),
            patch.object(app, "extract_youtube_url", return_value=None),
            patch.object(app, "_hydrate_pendings", AsyncMock()),
            patch.object(app, "_get_pending_description", return_value="Aguardando imagem"),
            patch.object(app, "classify_pending_response", AsyncMock(return_value="CANCEL")),
            patch.object(app, "_clear_all_pendings") as clear,
            patch.object(app, "send_message", AsyncMock()) as send,
        ):
            await app.handle_chat("5511", "deixa pra lá")

        clear.assert_called_once_with("5511")
        self.assertIn("Sem problema", send.await_args.args[1])
        self.assertNotIn("5511", app._processing)

    async def test_handle_chat_continues_pending_state_without_agent(self):
        with (
            patch.object(app, "_is_retroactive_transcription_request", return_value=False),
            patch.object(app, "extract_youtube_url", return_value=None),
            patch.object(app, "_hydrate_pendings", AsyncMock()),
            patch.object(app, "_get_pending_description", return_value="Aguardando imagem"),
            patch.object(app, "classify_pending_response", AsyncMock(return_value="CONTINUE")),
            patch.object(app, "_execute_pending", AsyncMock(return_value=True)) as execute,
            patch("aisha.agent.run_agent", AsyncMock()) as run_agent,
        ):
            await app.handle_chat("5511", "remova o fundo")

        execute.assert_awaited_once_with("5511", "remova o fundo")
        run_agent.assert_not_awaited()

    async def test_get_or_ask_timezone_profile_inference_and_pending(self):
        with patch.object(
            app,
            "get_profile",
            AsyncMock(return_value={"timezone": "Europe/Lisbon"}),
        ):
            self.assertEqual(
                await app.get_or_ask_timezone("5511", "amanhã às 8"),
                "Europe/Lisbon",
            )

        with (
            patch.object(app, "get_profile", AsyncMock(return_value=None)),
            patch.object(app, "infer_timezone", return_value="America/Manaus"),
            patch.object(app, "upsert_timezone", AsyncMock()) as upsert,
        ):
            self.assertEqual(
                await app.get_or_ask_timezone("5592", "amanhã às 8"),
                "America/Manaus",
            )
        upsert.assert_awaited_once_with("5592", "America/Manaus")

        def close_spawned(coro):
            coro.close()

        with (
            patch.object(app, "get_profile", AsyncMock(return_value=None)),
            patch.object(app, "infer_timezone", return_value=None),
            patch.object(app, "_spawn", side_effect=close_spawned),
        ):
            self.assertIsNone(
                await app.get_or_ask_timezone("999", "amanhã às 8"),
            )
        self.assertEqual(app._pending_timezone["999"], "amanhã às 8")

    async def test_execute_pending_timezone_retries_unrecognized_location(self):
        app._pending_timezone["5511"] = "me lembre amanhã"

        with (
            patch.object(app, "_resolve_tz_from_text", AsyncMock(return_value=None)),
            patch.object(app, "send_message", AsyncMock()) as send,
        ):
            handled = await app._execute_pending("5511", "em algum lugar")

        self.assertTrue(handled)
        self.assertEqual(app._pending_timezone["5511"], "me lembre amanhã")
        self.assertIn("Não consegui identificar", send.await_args.args[1])

    async def test_execute_pending_timezone_creates_reminder(self):
        app._pending_timezone["5511"] = "me lembre amanhã"
        scheduler = object()

        with (
            patch.object(app, "scheduler", scheduler, create=True),
            patch.object(
                app,
                "_resolve_tz_from_text",
                AsyncMock(return_value="America/Sao_Paulo"),
            ),
            patch.object(app, "upsert_timezone", AsyncMock()) as upsert_tz,
            patch.object(app, "classify", AsyncMock(return_value="REMINDER")),
            patch.object(
                app,
                "handle_reminder",
                AsyncMock(return_value="✅ Lembrete criado"),
            ) as reminder,
            patch.object(app, "increment_stat", AsyncMock()) as increment,
            patch.object(app, "send_message", AsyncMock()) as send,
        ):
            handled = await app._execute_pending("5511", "São Paulo")

        self.assertTrue(handled)
        self.assertNotIn("5511", app._pending_timezone)
        upsert_tz.assert_awaited_once_with("5511", "America/Sao_Paulo")
        reminder.assert_awaited_once_with(
            "5511",
            "me lembre amanhã",
            scheduler,
            "America/Sao_Paulo",
        )
        increment.assert_awaited_once_with("5511", "reminders_created")
        send.assert_awaited_once_with("5511", "✅ Lembrete criado")

    async def test_short_transcription_remains_in_whatsapp_messages(self):
        refined = " ".join(f"palavra{i}" for i in range(500))

        with (
            patch.object(app, "refine_transcription", AsyncMock(return_value=refined)),
            patch.object(app, "send_message", AsyncMock()) as send,
            patch.object(app, "send_text_document", AsyncMock()) as send_document,
        ):
            await app._send_refined_transcription("5511", "texto bruto")

        self.assertEqual(
            send.await_args_list,
            [
                unittest.mock.call("5511", "📝 Transcrição:"),
                unittest.mock.call("5511", refined),
            ],
        )
        send_document.assert_not_awaited()

    async def test_long_transcription_sends_preview_and_text_file(self):
        refined = " ".join(f"palavra{i}" for i in range(501))

        with (
            patch.object(app, "refine_transcription", AsyncMock(return_value=refined)),
            patch.object(app, "send_message", AsyncMock()) as send,
            patch.object(app, "send_text_document", AsyncMock()) as send_document,
        ):
            await app._send_refined_transcription("5511", "texto bruto")

        send.assert_awaited_once()
        preview_message = send.await_args.args[1]
        self.assertIn("501 palavras", preview_message)
        self.assertIn("palavra59…", preview_message)
        self.assertNotIn("palavra60", preview_message)
        send_document.assert_awaited_once_with(
            "5511",
            refined,
            filename="transcricao-aisha.txt",
            caption="Transcrição completa",
        )

    async def test_handle_audio_new_session_without_keyword_refines_transcript(self):
        client = MagicMock()
        client.get = AsyncMock(
            side_effect=[
                http_response(json_data={"url": "https://media.test/audio"}),
                http_response(content=b"audio"),
            ]
        )
        message = {"audio": {"id": "audio-1", "mime_type": "audio/ogg"}}

        with (
            patch.object(app, "http_client", client, create=True),
            patch.object(app, "send_message", AsyncMock()),
            patch.object(app, "increment_stat", AsyncMock()),
            patch.object(app, "transcribe_audio_bytes", AsyncMock(return_value="texto falado")),
            patch.object(app, "get_pending_image", return_value=None),
            patch.object(app, "_is_transcription_request", return_value=False),
            patch.object(app, "_contains_aisha", return_value=False),
            patch.object(app, "get_response_id", AsyncMock(return_value=None)),
            patch.object(app, "store_raw_transcription") as store_raw,
            patch.object(app, "_send_refined_transcription", AsyncMock()) as refine,
        ):
            await app.handle_audio("5511", message)

        store_raw.assert_called_once_with("5511", "texto falado")
        refine.assert_awaited_once_with("5511", "texto falado")
        self.assertNotIn("5511", app._processing)

    async def test_handle_audio_active_session_routes_to_agent_and_releases_lock(self):
        client = MagicMock()
        client.get = AsyncMock(
            side_effect=[
                http_response(json_data={"url": "https://media.test/audio"}),
                http_response(content=b"audio"),
            ]
        )
        message = {"audio": {"id": "audio-1"}}
        result = SimpleNamespace(
            response_id="new-response",
            image_bytes=None,
            text="feito",
            tools_called=None,
        )
        scheduler = object()

        with (
            patch.object(app, "http_client", client, create=True),
            patch.object(app, "scheduler", scheduler, create=True),
            patch.object(app, "send_message", AsyncMock()),
            patch.object(app, "increment_stat", AsyncMock()),
            patch.object(app, "transcribe_audio_bytes", AsyncMock(return_value="Aisha faça isso")),
            patch.object(app, "get_pending_image", return_value=None),
            patch.object(app, "_is_transcription_request", return_value=False),
            patch.object(app, "_contains_aisha", return_value=True),
            patch.object(app, "_strip_aisha", return_value="faça isso"),
            patch.object(app, "get_response_id", AsyncMock(return_value="previous")),
            patch.object(app, "store_raw_transcription"),
            patch("aisha.agent.run_agent", AsyncMock(return_value=result)) as run_agent,
            patch.object(app, "_deliver_agent_result", AsyncMock()) as deliver,
        ):
            await app.handle_audio("5511", message)

        run_agent.assert_awaited_once_with(
            user_input="faça isso",
            previous_response_id="previous",
            phone="5511",
            scheduler=scheduler,
        )
        deliver.assert_awaited_once_with("5511", result)
        self.assertNotIn("5511", app._processing)


if __name__ == "__main__":
    unittest.main()
