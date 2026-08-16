import unittest
from unittest.mock import patch

from tests.aisha_unit._helpers import async_http_client, configure_test_env, http_response

configure_test_env()

from aisha.skills import scheduled_task_store


class ScheduledTaskStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_returns_id_and_serializes_task(self):
        factory, client = async_http_client()
        client.post.return_value = http_response(201, [{"id": "task-1"}])
        task = scheduled_task_store.ScheduledTask(
            "5511", "Resumo", "Resuma notícias", "0 8 * * *", "America/Sao_Paulo"
        )

        with patch.object(scheduled_task_store.httpx, "AsyncClient", factory):
            result = await scheduled_task_store.save_task(task)

        self.assertEqual(result, "task-1")
        self.assertEqual(
            client.post.await_args.kwargs["json"],
            {
                "phone": "5511",
                "name": "Resumo",
                "prompt": "Resuma notícias",
                "cron_expression": "0 8 * * *",
                "timezone": "America/Sao_Paulo",
                "active": True,
            },
        )

    async def test_save_propagates_http_failure(self):
        factory, client = async_http_client()
        client.post.return_value = http_response(503)
        task = scheduled_task_store.ScheduledTask("5511", "n", "p", "* * * * *", "UTC")

        with patch.object(scheduled_task_store.httpx, "AsyncClient", factory):
            with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                await scheduled_task_store.save_task(task)

    async def test_get_queries_return_empty_lists(self):
        factory, client = async_http_client()
        client.get.side_effect = [http_response(200, []), http_response(200, [])]

        with patch.object(scheduled_task_store.httpx, "AsyncClient", factory):
            self.assertEqual(await scheduled_task_store.get_tasks("5511"), [])
            self.assertEqual(await scheduled_task_store.get_all_active_tasks(), [])

        first_params = client.get.await_args_list[0].kwargs["params"]
        second_params = client.get.await_args_list[1].kwargs["params"]
        self.assertEqual(first_params["phone"], "eq.5511")
        self.assertEqual(first_params["active"], "eq.true")
        self.assertEqual(second_params["active"], "eq.true")

    async def test_get_propagates_http_failure(self):
        factory, client = async_http_client()
        client.get.return_value = http_response(500)

        with patch.object(scheduled_task_store.httpx, "AsyncClient", factory):
            with self.assertRaisesRegex(RuntimeError, "HTTP 500"):
                await scheduled_task_store.get_tasks("5511")

    async def test_mutations_send_expected_payloads(self):
        factory, client = async_http_client()

        with patch.object(scheduled_task_store.httpx, "AsyncClient", factory):
            await scheduled_task_store.update_job_id("task-1", "job-1")
            await scheduled_task_store.deactivate_task("task-1")
            await scheduled_task_store.update_task("task-1", name="Novo", timezone="UTC")

        payloads = [call.kwargs["json"] for call in client.patch.await_args_list]
        self.assertEqual(
            payloads,
            [
                {"job_id": "job-1"},
                {"active": False},
                {"name": "Novo", "timezone": "UTC"},
            ],
        )
