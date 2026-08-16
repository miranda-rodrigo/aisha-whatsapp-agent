"""Testes unitários da skill de tarefas agendadas."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.aisha_unit._helpers import configure_test_env, namespace

configure_test_env()

from aisha.skills import scheduled_task


class ScheduledTaskPureTests(unittest.TestCase):
    def test_detecta_intencao_e_normaliza_texto(self):
        self.assertTrue(
            scheduled_task.is_scheduled_task_intent(
                "Toda segunda me mande um relatório de tecnologia"
            )
        )
        self.assertFalse(scheduled_task.is_scheduled_task_intent("bom dia"))
        self.assertEqual(scheduled_task._normalize_text("  Versículos: AÇÃO!  "), "versiculos acao")

    @patch.object(scheduled_task, "CronTrigger")
    def test_parse_cron_valida_cinco_campos(self, trigger):
        scheduled_task._parse_cron("0 9 * * 1", "America/Sao_Paulo")
        trigger.assert_called_once_with(
            minute="0",
            hour="9",
            day="*",
            month="*",
            day_of_week="1",
            timezone="America/Sao_Paulo",
        )
        with self.assertRaises(ValueError):
            scheduled_task._parse_cron("0 9 * *", "UTC")

    def test_resolve_referencia_por_numero_e_texto(self):
        rows = [
            {"name": "Mercado", "prompt": "Resumo financeiro"},
            {"name": "Versículos", "prompt": "Reflexão bíblica diária"},
        ]
        row, error = scheduled_task._resolve_task_reference(
            rows, scheduled_task.TaskExtraction(action="edit", task_number=2)
        )
        self.assertIsNone(error)
        self.assertEqual(row["name"], "Versículos")

        row, error = scheduled_task._resolve_task_reference(
            rows,
            scheduled_task.TaskExtraction(
                action="edit", task_reference_text="versículos"
            ),
        )
        self.assertIsNone(error)
        self.assertEqual(row["name"], "Versículos")

    def test_referencia_ambigua_pede_numero(self):
        rows = [
            {"name": "Notícias A", "prompt": "Resumo diário"},
            {"name": "Notícias B", "prompt": "Resumo diário"},
        ]
        row, error = scheduled_task._resolve_task_reference(
            rows, scheduled_task.TaskExtraction(action="edit", task_reference_text="notícias")
        )
        self.assertIsNone(row)
        self.assertIn("número", error)


class ScheduledTaskAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_delega_conforme_acao(self):
        scheduler = MagicMock()
        cases = [
            ("list", "_handle_list"),
            ("cancel", "_handle_cancel"),
            ("edit", "_handle_edit"),
            ("create", "_handle_create"),
        ]
        for action, target in cases:
            extraction = scheduled_task.TaskExtraction(action=action)
            with self.subTest(action=action), patch.object(
                scheduled_task, "_extract", AsyncMock(return_value=extraction)
            ), patch.object(scheduled_task, target, AsyncMock(return_value=action)) as handler:
                result = await scheduled_task.handle_scheduled_task("5511", "texto", scheduler, "UTC")
                self.assertEqual(result, action)
                handler.assert_awaited_once()

    async def test_criacao_valida_e_persiste(self):
        scheduler = MagicMock()
        invalid = scheduled_task.TaskExtraction(action="create", prompt="Faça algo")
        self.assertIn("Não entendi", await scheduled_task._handle_create("5511", invalid, scheduler, "UTC"))

        valid = scheduled_task.TaskExtraction(
            action="create",
            name="Mercado",
            prompt="Resuma o mercado",
            cron_expression="0 8 * * *",
            cron_readable="todo dia às 08:00",
        )
        with patch.object(scheduled_task, "_parse_cron"), patch.object(
            scheduled_task, "save_task", AsyncMock(return_value="t1")
        ) as save, patch.object(
            scheduled_task, "_schedule_job", AsyncMock(return_value="j1")
        ) as schedule, patch.object(scheduled_task, "update_job_id", AsyncMock()) as update:
            result = await scheduled_task._handle_create("5511", valid, scheduler, "UTC")
        self.assertIn("Tarefa agendada criada", result)
        self.assertEqual(save.await_args.args[0].name, "Mercado")
        schedule.assert_awaited_once()
        update.assert_awaited_once_with("t1", "j1")

    async def test_edicao_altera_apenas_campos_informados(self):
        scheduler = MagicMock()
        scheduler.remove_schedule = AsyncMock()
        row = {
            "id": "t1",
            "name": "Versículos",
            "prompt": "Envie os versículos",
            "cron_expression": "0 8 * * *",
            "timezone": "UTC",
            "job_id": "j1",
        }
        ex = scheduled_task.TaskExtraction(
            action="edit", task_number=1, new_prompt="Envie e faça uma reflexão"
        )
        with patch.object(scheduled_task, "get_tasks", AsyncMock(return_value=[row])), patch.object(
            scheduled_task, "update_task", AsyncMock()
        ) as update_task, patch.object(
            scheduled_task, "_schedule_job", AsyncMock(return_value="j2")
        ), patch.object(scheduled_task, "update_job_id", AsyncMock()):
            result = await scheduled_task._handle_edit("5511", ex, scheduler, "UTC")
        self.assertIn("atualizada", result)
        update_task.assert_awaited_once_with(
            "t1", prompt="Envie e faça uma reflexão"
        )
        scheduler.remove_schedule.assert_awaited_once_with("j1")

    async def test_execucao_envia_resultado_e_trata_falha(self):
        output = [
            namespace(
                type="message",
                content=[namespace(type="output_text", text="Resultado atualizado")],
            )
        ]
        response = namespace(id="resp", status="completed", output=output)
        with patch.object(
            scheduled_task._client.responses, "create", AsyncMock(return_value=response)
        ), patch.object(scheduled_task, "_send_whatsapp", AsyncMock()) as send:
            await scheduled_task._execute_task("5511", "t1", "Relatório", "Pesquise")
        send.assert_awaited_once_with("5511", "📋 *Relatório*\n\nResultado atualizado")

        with patch.object(
            scheduled_task._client.responses, "create", AsyncMock(side_effect=RuntimeError("offline"))
        ), patch.object(scheduled_task, "_send_whatsapp", AsyncMock()) as send:
            await scheduled_task._execute_task("5511", "t1", "Relatório", "Pesquise")
        self.assertIn("offline", send.await_args.args[1])


if __name__ == "__main__":
    unittest.main()
