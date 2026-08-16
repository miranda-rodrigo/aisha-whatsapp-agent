import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import async_http_client, configure_test_env, http_response

configure_test_env()

from aisha import session


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_returns_none_for_missing_session(self):
        factory, client = async_http_client()
        client.get.return_value = http_response(200, [])

        with patch.object(session.httpx, "AsyncClient", factory):
            self.assertIsNone(await session.get_response_id("5511"))

    async def test_get_returns_active_response_id(self):
        row = {
            "response_id": "resp-1",
            "last_active": datetime.now(timezone.utc).isoformat(),
        }
        factory, client = async_http_client()
        client.get.return_value = http_response(200, [row])

        with patch.object(session.httpx, "AsyncClient", factory):
            self.assertEqual(await session.get_response_id("5511"), "resp-1")

    async def test_get_deletes_expired_session(self):
        last_active = datetime.now(timezone.utc) - timedelta(
            minutes=session.SESSION_TIMEOUT_MINUTES + 1
        )
        factory, client = async_http_client()
        client.get.return_value = http_response(
            200, [{"response_id": "old", "last_active": last_active.isoformat()}]
        )

        with (
            patch.object(session.httpx, "AsyncClient", factory),
            patch.object(session, "delete_session", AsyncMock()) as delete,
        ):
            self.assertIsNone(await session.get_response_id("5511"))

        delete.assert_awaited_once_with("5511")

    async def test_upsert_and_delete_use_phone_filter(self):
        factory, client = async_http_client()

        with patch.object(session.httpx, "AsyncClient", factory):
            await session.upsert_session("5511", "resp-1")
            await session.delete_session("5511")

        payload = client.post.await_args.kwargs["json"]
        self.assertEqual((payload["phone"], payload["response_id"]), ("5511", "resp-1"))
        datetime.fromisoformat(payload["last_active"])
        self.assertEqual(client.delete.await_args.kwargs["params"], {"phone": "eq.5511"})
