import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from tests.aisha_unit._helpers import async_http_client, configure_test_env, http_response

configure_test_env()

from aisha.skills import reminder_store


class ReminderStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_returns_id_and_serializes_optional_fields(self):
        factory, client = async_http_client()
        client.post.return_value = http_response(201, [{"id": "rem-1"}])
        reminder = reminder_store.Reminder(
            phone="5511",
            message="Beber água",
            scheduled_at=datetime(2026, 8, 16, 12, tzinfo=timezone.utc),
            timezone="America/Sao_Paulo",
            is_recurring=True,
            rrule="FREQ=DAILY",
            job_id="job-1",
        )

        with patch.object(reminder_store.httpx, "AsyncClient", factory):
            result = await reminder_store.save_reminder(reminder)

        self.assertEqual(result, "rem-1")
        payload = client.post.await_args.kwargs["json"]
        self.assertEqual(payload["rrule"], "FREQ=DAILY")
        self.assertEqual(payload["job_id"], "job-1")
        self.assertTrue(payload["is_recurring"])

    async def test_save_propagates_http_failure(self):
        factory, client = async_http_client()
        client.post.return_value = http_response(500)
        reminder = reminder_store.Reminder(
            "5511", "msg", datetime.now(timezone.utc), "UTC"
        )

        with patch.object(reminder_store.httpx, "AsyncClient", factory):
            with self.assertRaisesRegex(RuntimeError, "HTTP 500"):
                await reminder_store.save_reminder(reminder)

    async def test_get_returns_empty_result_with_expected_filters(self):
        factory, client = async_http_client()
        client.get.return_value = http_response(200, [])

        with patch.object(reminder_store.httpx, "AsyncClient", factory):
            result = await reminder_store.get_reminders("5511", "sent")

        self.assertEqual(result, [])
        params = client.get.await_args.kwargs["params"]
        self.assertEqual((params["phone"], params["status"]), ("eq.5511", "eq.sent"))

    async def test_cancel_checks_http_failure(self):
        factory, client = async_http_client()
        client.patch.return_value = http_response(409)

        with patch.object(reminder_store.httpx, "AsyncClient", factory):
            with self.assertRaisesRegex(RuntimeError, "HTTP 409"):
                await reminder_store.cancel_reminder("rem-1")

    async def test_update_operations_send_expected_changes(self):
        factory, client = async_http_client()
        when = datetime(2026, 8, 17, 9, tzinfo=timezone.utc)

        with patch.object(reminder_store.httpx, "AsyncClient", factory):
            await reminder_store.update_job_id("rem-1", "job-1")
            await reminder_store.mark_sent("rem-1")
            await reminder_store.update_reminder("rem-1", when, "FREQ=WEEKLY")

        payloads = [call.kwargs["json"] for call in client.patch.await_args_list]
        self.assertEqual(payloads[0], {"job_id": "job-1"})
        self.assertEqual(payloads[1], {"status": "sent"})
        self.assertEqual(
            payloads[2],
            {"scheduled_at": when.isoformat(), "status": "pending", "rrule": "FREQ=WEEKLY"},
        )
