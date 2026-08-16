import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import async_http_client, configure_test_env, http_response

configure_test_env()

from aisha.skills import pending_store


class PendingStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_upsert_persists_payload_and_acceptable_blob(self):
        factory, client = async_http_client()
        client.post.return_value = http_response(201)

        with patch.object(pending_store.httpx, "AsyncClient", factory):
            await pending_store.upsert_pending("5511", "image", {"x": 1}, 60, "abc")

        body = client.post.await_args.kwargs["json"]
        self.assertEqual(body["blob_b64"], "abc")
        self.assertEqual(body["payload"], {"x": 1})
        self.assertGreater(datetime.fromisoformat(body["expires_at"]), datetime.now(timezone.utc))

    async def test_upsert_omits_oversized_blob_and_handles_failure(self):
        factory, client = async_http_client()
        client.post.return_value = http_response(500, text="unavailable")

        with (
            patch.object(pending_store, "_MAX_BLOB_CHARS", 2),
            patch.object(pending_store.httpx, "AsyncClient", factory),
            self.assertLogs(pending_store.log, level="WARNING") as logs,
        ):
            await pending_store.upsert_pending("5511", "image", {}, 60, "abc")

        self.assertNotIn("blob_b64", client.post.await_args.kwargs["json"])
        self.assertTrue(any("Failed to persist" in message for message in logs.output))

    async def test_get_returns_none_for_http_failure_or_empty_result(self):
        for response in (http_response(503), http_response(200, [])):
            factory, client = async_http_client()
            client.get.return_value = response
            with self.subTest(status=response.status_code), patch.object(
                pending_store.httpx, "AsyncClient", factory
            ):
                self.assertIsNone(await pending_store.get_pending("5511", "image"))

    async def test_get_clears_expired_row(self):
        expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        factory, client = async_http_client()
        client.get.return_value = http_response(200, [{"expires_at": expired, "payload": {}}])

        with (
            patch.object(pending_store.httpx, "AsyncClient", factory),
            patch.object(pending_store, "clear_pending", AsyncMock()) as clear,
        ):
            self.assertIsNone(await pending_store.get_pending("5511", "image"))

        clear.assert_awaited_once_with("5511", "image")

    async def test_get_returns_live_row(self):
        row = {
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
            "payload": {"value": 1},
        }
        factory, client = async_http_client()
        client.get.return_value = http_response(200, [row])

        with patch.object(pending_store.httpx, "AsyncClient", factory):
            self.assertEqual(await pending_store.get_pending("5511", "kind"), row)

    async def test_clear_variants_use_expected_filters(self):
        factory, client = async_http_client()
        with patch.object(pending_store.httpx, "AsyncClient", factory):
            await pending_store.clear_pending("5511", "image")
            await pending_store.clear_all_pending("5511")

        self.assertEqual(client.delete.await_count, 2)
        self.assertEqual(
            client.delete.await_args_list[0].kwargs["params"],
            {"phone": "eq.5511", "kind": "eq.image"},
        )
        self.assertEqual(client.delete.await_args_list[1].kwargs["params"], {"phone": "eq.5511"})
