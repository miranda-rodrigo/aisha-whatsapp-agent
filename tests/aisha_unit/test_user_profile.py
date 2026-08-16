import unittest
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import async_http_client, configure_test_env, http_response

configure_test_env()

from aisha import user_profile


class UserProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_profile_returns_row_or_none(self):
        profile = {"language": "pt", "stats": {"messages": 2}}
        for rows, expected in (([profile], profile), ([], None)):
            factory, client = async_http_client()
            client.get.return_value = http_response(200, rows)
            with self.subTest(rows=rows), patch.object(
                user_profile.httpx, "AsyncClient", factory
            ):
                self.assertEqual(await user_profile.get_profile("5511"), expected)

    async def test_get_profile_propagates_http_failure(self):
        factory, client = async_http_client()
        client.get.return_value = http_response(500)

        with patch.object(user_profile.httpx, "AsyncClient", factory):
            with self.assertRaisesRegex(RuntimeError, "HTTP 500"):
                await user_profile.get_profile("5511")

    async def test_profile_upserts_send_specific_fields(self):
        factory, client = async_http_client()

        with patch.object(user_profile.httpx, "AsyncClient", factory):
            await user_profile.upsert_timezone("5511", "UTC")
            await user_profile.upsert_context("5511", "contexto")
            await user_profile.upsert_language("5511", "pt-BR")

        payloads = [call.kwargs["json"] for call in client.post.await_args_list]
        self.assertEqual(payloads[0]["timezone"], "UTC")
        self.assertEqual(payloads[1]["personal_context"], "contexto")
        self.assertEqual(payloads[2]["language"], "pt-BR")
        for payload in payloads:
            self.assertEqual(payload["phone"], "5511")
            self.assertIn("updated_at", payload)

    async def test_increment_stat_succeeds_without_fallback(self):
        factory, client = async_http_client()
        client.post.return_value = http_response(204)

        with (
            patch.object(user_profile.httpx, "AsyncClient", factory),
            patch.object(user_profile, "_increment_stat_fallback", AsyncMock()) as fallback,
        ):
            await user_profile.increment_stat("5511", "messages")

        fallback.assert_not_awaited()
        self.assertEqual(
            client.post.await_args.kwargs["json"],
            {"p_phone": "5511", "p_key": "messages"},
        )

    async def test_increment_stat_uses_fallback_after_rpc_failure(self):
        factory, client = async_http_client()
        client.post.return_value = http_response(404)

        with (
            patch.object(user_profile.httpx, "AsyncClient", factory),
            patch.object(user_profile, "_increment_stat_fallback", AsyncMock()) as fallback,
            self.assertLogs(user_profile.log, level="WARNING"),
        ):
            await user_profile.increment_stat("5511", "messages")

        fallback.assert_awaited_once_with("5511", "messages")

    async def test_fallback_increments_existing_and_missing_stats(self):
        cases = [
            ({"stats": {"messages": 2}}, 3),
            (None, 1),
        ]
        for profile, expected in cases:
            factory, client = async_http_client()
            with (
                self.subTest(profile=profile),
                patch.object(user_profile, "get_profile", AsyncMock(return_value=profile)),
                patch.object(user_profile.httpx, "AsyncClient", factory),
            ):
                await user_profile._increment_stat_fallback("5511", "messages")

            self.assertEqual(
                client.post.await_args.kwargs["json"]["stats"]["messages"],
                expected,
            )
