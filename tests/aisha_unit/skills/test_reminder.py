"""Testes unitários da skill de lembretes."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

from tests.aisha_unit._helpers import configure_test_env

configure_test_env()

from aisha.skills import reminder


class ReminderPureTests(unittest.TestCase):
    def test_detecta_intencao_sem_falso_positivo_obvio(self):
        self.assertTrue(reminder.is_reminder_intent("Me lembra da consulta amanhã"))
        self.assertTrue(reminder.is_reminder_intent("cancela o lembrete 2"))
        self.assertFalse(reminder.is_reminder_intent("qual é a previsão do tempo?"))

    def test_parse_iso_converte_horario_local_para_utc(self):
        parsed = reminder._parse_dt_iso("2026-08-16T10:30:00", "America/Sao_Paulo")
        self.assertEqual(parsed, datetime(2026, 8, 16, 13, 30, tzinfo=timezone.utc))
        self.assertIsNone(reminder._parse_dt_iso("data inválida", "America/Sao_Paulo"))

    def test_resolve_prefere_iso_e_recua_para_texto(self):
        expected = datetime(2030, 1, 1, tzinfo=timezone.utc)
        with patch.object(reminder, "_parse_dt_iso", return_value=expected) as parse_iso, patch.object(
            reminder, "_parse_dt_raw"
        ) as parse_raw:
            self.assertIs(reminder._resolve_dt("2030-01-01T00:00:00", "amanhã", "UTC"), expected)
        parse_iso.assert_called_once()
        parse_raw.assert_not_called()

    def test_link_calendario_contem_intervalo_e_timezone(self):
        start = datetime(2030, 1, 2, 12, tzinfo=timezone.utc)
        query = parse_qs(urlparse(reminder._gcal_link("Consulta", start, "America/Sao_Paulo", 30)).query)
        self.assertEqual(query["text"], ["Consulta"])
        self.assertEqual(query["dates"], ["20300102T120000Z/20300102T123000Z"])
        self.assertEqual(query["ctz"], ["America/Sao_Paulo"])

    @patch.object(reminder, "CronTrigger")
    def test_rrule_semanal_vira_cron(self, cron_trigger):
        first = datetime(2030, 1, 1, 8, 45, tzinfo=timezone.utc)
        reminder._rrule_to_trigger("FREQ=WEEKLY;BYDAY=MO,WE,FR", first)
        cron_trigger.assert_called_once_with(
            hour=8, minute=45, timezone="UTC", day_of_week="mon,wed,fri"
        )


class ReminderAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_delega_conforme_acao(self):
        scheduler = MagicMock()
        cases = [
            ("list", "_handle_list"),
            ("cancel", "_handle_cancel"),
            ("edit", "_handle_edit"),
            ("create", "_handle_create"),
        ]
        for action, target in cases:
            with self.subTest(action=action), patch.object(
                reminder, "_extract", AsyncMock(return_value=reminder.ReminderExtraction(action=action))
            ), patch.object(reminder, target, AsyncMock(return_value=action)) as handler:
                result = await reminder.handle_reminder("5511", "texto", scheduler, "UTC")
                self.assertEqual(result, action)
                handler.assert_awaited_once()

    async def test_agenda_job_unico_com_antecedencia(self):
        scheduler = MagicMock()
        scheduler.add_schedule = AsyncMock(return_value=123)
        event_at = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
        with patch.object(reminder, "DateTrigger") as date_trigger:
            result = await reminder._schedule_job(
                "r1", "5511", "Consulta", event_at, 15, False, None, scheduler
            )
        self.assertEqual(result, "123")
        date_trigger.assert_called_once_with(run_time=event_at - timedelta(minutes=15))
        kwargs = scheduler.add_schedule.await_args.kwargs
        self.assertEqual(kwargs["id"], "r1")
        self.assertEqual(kwargs["kwargs"]["message"], "Consulta")

    async def test_criacao_valida_entrada_e_persiste(self):
        scheduler = MagicMock()
        missing = reminder.ReminderExtraction(action="create", message="Consulta")
        self.assertIn("diga quando", await reminder._handle_create("5511", missing, scheduler, "UTC"))

        event_at = datetime(2099, 1, 1, 12, tzinfo=timezone.utc)
        valid = reminder.ReminderExtraction(
            action="create",
            message="Consulta",
            datetime_iso="2099-01-01T12:00:00",
            lead_minutes=10,
        )
        with patch.object(reminder, "_resolve_dt", return_value=event_at), patch.object(
            reminder, "save_reminder", AsyncMock(return_value="r1")
        ) as save, patch.object(reminder, "_schedule_job", AsyncMock(return_value="j1")) as schedule, patch.object(
            reminder, "update_job_id", AsyncMock()
        ) as update:
            result = await reminder._handle_create("5511", valid, scheduler, "UTC")
        self.assertIn("Lembrete criado", result)
        self.assertEqual(save.await_args.args[0].message, "Consulta")
        self.assertEqual(schedule.await_args.kwargs["lead_minutes"], 10)
        update.assert_awaited_once_with("r1", "j1")

    async def test_cancelamento_remove_registro_e_agendamento(self):
        scheduler = MagicMock()
        scheduler.remove_schedule = AsyncMock()
        rows = [{"id": "r1", "message": "Consulta", "job_id": "j1"}]
        ex = reminder.ReminderExtraction(action="cancel", reminder_number=1)
        with patch.object(reminder, "get_reminders", AsyncMock(return_value=rows)), patch.object(
            reminder, "cancel_reminder", AsyncMock()
        ) as cancel:
            result = await reminder._handle_cancel("5511", ex, scheduler)
        self.assertIn("Consulta", result)
        cancel.assert_awaited_once_with("r1")
        scheduler.remove_schedule.assert_awaited_once_with("j1")


if __name__ == "__main__":
    unittest.main()
