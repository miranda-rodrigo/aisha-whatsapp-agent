"""Testes de segurança, deduplicação e webhook."""

import hashlib
import hmac
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, call, patch

from tests.aisha_unit._helpers import http_response, namespace

import aisha.app as app


def webhook_body(
    *,
    sender: str = "5511999999999",
    msg_id: str = "wamid.1",
    msg_type: str = "text",
    include_contacts: bool = True,
):
    value = {
        "metadata": {"display_phone_number": "5511000000000"},
        "messages": [
            {
                "from": sender,
                "id": msg_id,
                "type": msg_type,
                msg_type: {"body": "olá"} if msg_type == "text" else {"id": "media-1"},
            }
        ],
    }
    if include_contacts:
        value["contacts"] = [{"wa_id": sender}]
    return {"entry": [{"changes": [{"value": value}]}]}


class WebhookSecurityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        app._processed_messages.clear()
        app._last_reply_time.clear()
        app._processing.clear()
        app._pending_timezone.clear()

    def tearDown(self):
        app._processed_messages.clear()
        app._last_reply_time.clear()
        app._processing.clear()
        app._pending_timezone.clear()

    def test_verify_signature_accepts_valid_hmac_and_rejects_bad_header(self):
        raw = b'{"entry":[]}'
        secret = "app-secret"
        digest = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()

        with patch.object(app, "WHATSAPP_APP_SECRET", secret):
            self.assertTrue(app._verify_signature(raw, f"sha256={digest}"))
            self.assertFalse(app._verify_signature(raw, "sha256=wrong"))
            self.assertFalse(app._verify_signature(raw, None))

    def test_verify_signature_is_disabled_without_secret(self):
        with patch.object(app, "WHATSAPP_APP_SECRET", ""):
            self.assertTrue(app._verify_signature(b"payload", None))

    def test_dedup_rejects_repeat_and_expires_old_entries(self):
        app._processed_messages["expired"] = 100.0

        with patch.object(app.time, "time", return_value=401.0):
            self.assertFalse(app._is_duplicate("fresh"))
            self.assertTrue(app._is_duplicate("fresh"))

        self.assertNotIn("expired", app._processed_messages)

    async def test_receive_webhook_validates_and_spawns_processing(self):
        raw = json.dumps(webhook_body()).encode()
        request = namespace(
            body=AsyncMock(return_value=raw),
            headers={"X-Hub-Signature-256": "sha256=value"},
        )
        process = MagicMock(return_value="processing")

        with (
            patch.object(app, "_verify_signature", return_value=True),
            patch.object(app, "_spawn") as spawn,
            patch.object(app, "_process_webhook", new=process),
        ):
            result = await app.receive_webhook(request)

        self.assertEqual(result, {"status": "ok"})
        process.assert_called_once()
        spawn.assert_called_once_with("processing")

    async def test_receive_webhook_rejects_invalid_signature(self):
        request = namespace(
            body=AsyncMock(return_value=b"{}"),
            headers={},
        )

        with patch.object(app, "_verify_signature", return_value=False):
            with self.assertRaises(app.HTTPException) as raised:
                await app.receive_webhook(request)

        self.assertEqual(raised.exception.status_code, 403)

    async def test_process_webhook_routes_allowed_text_and_deduplicates(self):
        body = webhook_body()

        with (
            patch.object(app, "ALLOWED_NUMBERS", {"5511999999999"}),
            patch.object(app, "handle_chat", AsyncMock()) as handle_chat,
        ):
            await app._process_webhook(body)
            await app._process_webhook(body)

        handle_chat.assert_awaited_once_with("5511999999999", "olá")

    async def test_process_webhook_ignores_own_or_disallowed_sender(self):
        own = webhook_body(sender="5511000000000", msg_id="own")
        disallowed = webhook_body(sender="5511888888888", msg_id="other")

        with (
            patch.object(app, "ALLOWED_NUMBERS", {"5511999999999"}),
            patch.object(app, "handle_chat", AsyncMock()) as handle_chat,
        ):
            await app._process_webhook(own)
            await app._process_webhook(disallowed)

        handle_chat.assert_not_awaited()

    async def test_process_webhook_sends_fallback_for_unsupported_type(self):
        body = webhook_body(msg_type="sticker")

        with (
            patch.object(app, "ALLOWED_NUMBERS", {"5511999999999"}),
            patch.object(app, "send_message", AsyncMock()) as send,
        ):
            await app._process_webhook(body)

        send.assert_awaited_once_with(
            "5511999999999",
            "Tipo 'sticker' ainda não suportado.",
        )

    async def test_send_message_posts_each_chunk_and_tracks_reply_time(self):
        client = MagicMock()
        client.post = AsyncMock(
            side_effect=[
                http_response(status_code=200),
                http_response(status_code=500, text="failed"),
            ]
        )

        with (
            patch.object(app, "http_client", client, create=True),
            patch.object(app, "split_whatsapp_text", return_value=["um", "dois"]),
            patch.object(app.time, "time", return_value=11.0),
        ):
            await app.send_message("5511", "texto longo")

        self.assertEqual(
            client.post.await_args_list,
            [
                call(
                    f"{app.GRAPH_API_URL}/messages",
                    json={
                        "messaging_product": "whatsapp",
                        "to": "5511",
                        "type": "text",
                        "text": {"body": "um"},
                    },
                ),
                call(
                    f"{app.GRAPH_API_URL}/messages",
                    json={
                        "messaging_product": "whatsapp",
                        "to": "5511",
                        "type": "text",
                        "text": {"body": "dois"},
                    },
                ),
            ],
        )
        self.assertEqual(app._last_reply_time["5511"], 11.0)

    async def test_send_text_document_uploads_utf8_and_sends_media_id(self):
        client = MagicMock()
        client.post = AsyncMock(
            side_effect=[
                http_response(status_code=200, json_data={"id": "media-1"}),
                http_response(status_code=200),
            ]
        )

        with (
            patch.object(app, "http_client", client, create=True),
            patch.object(app.time, "time", return_value=12.0),
        ):
            await app.send_text_document(
                "5511",
                "transcrição completa",
                filename="transcricao.txt",
                caption="Transcrição completa",
            )

        upload = client.post.await_args_list[0]
        self.assertEqual(upload.args, (f"{app.GRAPH_API_URL}/media",))
        self.assertEqual(
            upload.kwargs["files"]["file"],
            ("transcricao.txt", "transcrição completa".encode("utf-8"), "text/plain"),
        )
        self.assertEqual(
            upload.kwargs["data"],
            {"messaging_product": "whatsapp", "type": "text/plain"},
        )
        self.assertEqual(
            client.post.await_args_list[1],
            call(
                f"{app.GRAPH_API_URL}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": "5511",
                    "type": "document",
                    "document": {
                        "id": "media-1",
                        "filename": "transcricao.txt",
                        "caption": "Transcrição completa",
                    },
                },
            ),
        )
        self.assertEqual(app._last_reply_time["5511"], 12.0)


if __name__ == "__main__":
    unittest.main()
