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

    def test_link_calendario_contem_intervalo_e_timezone(self):
        start = datetime(2030, 1, 2, 12, tzinfo=timezone.utc)
        query = parse_qs(urlparse(reminder._gcal_link("Consulta", start, "America/Sao_Paulo", 30)).query)
        self.assertEqual(query["text"], ["Consulta"])
        self.assertEqual(query["dates"], ["20300102T120000Z/20300102T123000Z"])
        self.assertEqual(query["ctz"], ["America/Sao_Paulo"])

    @patch.object(reminder, "CronTrigger")
    def test_rrule_semanal_vira_cron_no_fuso_do_usuario(self, cron_trigger):
        first = datetime(2030, 1, 1, 8, 45, tzinfo=timezone.utc)
        reminder._rrule_to_trigger("FREQ=WEEKLY;BYDAY=MO,WE,FR", first, "America/Sao_Paulo")
        # 08:45 UTC = 05:45 em São Paulo (UTC-3)
        cron_trigger.assert_called_once_with(
            hour=5, minute=45, timezone="America/Sao_Paulo", day_of_week="mon,wed,fri"
        )

    @patch.object(reminder, "CronTrigger")
    def test_rrule_com_prefixo_cron_usa_os_cinco_campos(self, cron_trigger):
        first = datetime(2030, 1, 1, 8, 45, tzinfo=timezone.utc)
        reminder._rrule_to_trigger("CRON:0 9 * * 1", first, "America/Sao_Paulo")
        cron_trigger.assert_called_once_with(
            minute="0",
            hour="9",
            day="*",
            month="*",
            day_of_week="1",
            timezone="America/Sao_Paulo",
        )

    @patch.object(reminder, "CronTrigger")
    def test_rrule_cron_invalido_recua_para_diario(self, cron_trigger):
        first = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
        reminder._rrule_to_trigger("CRON:invalido", first, "UTC")
        cron_trigger.assert_called_once_with(hour=12, minute=0, timezone="UTC", day="*")


class ReminderAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_prefere_iso_e_recua_para_texto(self):
        expected = datetime(2030, 1, 1, tzinfo=timezone.utc)
        with patch.object(reminder, "_parse_dt_iso", return_value=expected) as parse_iso, patch.object(
            reminder, "_parse_dt_raw"
        ) as parse_raw:
            result = await reminder._resolve_dt("2030-01-01T00:00:00", "amanhã", "UTC")
        self.assertIs(result, expected)
        parse_iso.assert_called_once()
        parse_raw.assert_not_called()

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
        with patch.object(reminder, "_resolve_dt", AsyncMock(return_value=event_at)), patch.object(
            reminder, "save_reminder", AsyncMock(return_value="r1")
        ) as save, patch.object(reminder, "_schedule_job", AsyncMock(return_value="j1")) as schedule, patch.object(
            reminder, "update_job_id", AsyncMock()
        ) as update:
            result = await reminder._handle_create("5511", valid, scheduler, "UTC")
        self.assertIn("Lembrete criado", result)
        self.assertEqual(save.await_args.args[0].message, "Consulta")
        self.assertEqual(schedule.await_args.kwargs["lead_minutes"], 10)
        update.assert_awaited_once_with("r1", "j1")

    async def test_agenda_job_com_fire_no_passado_dispara_imediatamente(self):
        scheduler = MagicMock()
        scheduler.add_schedule = AsyncMock(return_value=1)
        now = datetime.now(timezone.utc)
        event_at = now + timedelta(minutes=5)  # aviso de 15 min cairia no passado
        with patch.object(reminder, "DateTrigger") as date_trigger:
            await reminder._schedule_job(
                "r1", "5511", "Consulta", event_at, 15, False, None, scheduler
            )
        run_time = date_trigger.call_args.kwargs["run_time"]
        self.assertGreater(run_time, now)
        self.assertLess(run_time, now + timedelta(seconds=30))

    async def test_disparo_marca_sent_apenas_para_nao_recorrente(self):
        with patch.object(reminder, "_send_whatsapp", AsyncMock()) as send, patch.object(
            reminder, "mark_sent", AsyncMock()
        ) as mark:
            await reminder._fire_reminder("5511", "r1", "Consulta", is_recurring=False,
                                          event_display="02/01 às 12:00")
        self.assertIn("(02/01 às 12:00)", send.await_args.args[1])
        mark.assert_awaited_once_with("r1")

        with patch.object(reminder, "_send_whatsapp", AsyncMock()), patch.object(
            reminder, "mark_sent", AsyncMock()
        ) as mark:
            await reminder._fire_reminder("5511", "r2", "Remédio", is_recurring=True)
        mark.assert_not_awaited()

    async def test_restore_reagenda_futuros_e_avisa_atrasados(self):
        scheduler = MagicMock()
        scheduler.remove_schedule = AsyncMock()
        now = datetime.now(timezone.utc)
        rows = [
            {  # futuro: deve ser reagendado
                "id": "r-futuro", "phone": "5511", "message": "Consulta",
                "scheduled_at": (now + timedelta(hours=2)).isoformat(),
                "timezone": "UTC", "is_recurring": False, "rrule": None, "job_id": "r-futuro",
            },
            {  # atrasado há pouco: aviso + sent
                "id": "r-atrasado", "phone": "5511", "message": "Reunião",
                "scheduled_at": (now - timedelta(hours=1)).isoformat(),
                "timezone": "UTC", "is_recurring": False, "rrule": None, "job_id": "r-atrasado",
            },
            {  # atrasado antigo: sent em silêncio
                "id": "r-antigo", "phone": "5511", "message": "Velho",
                "scheduled_at": (now - timedelta(days=3)).isoformat(),
                "timezone": "UTC", "is_recurring": False, "rrule": None, "job_id": "r-antigo",
            },
            {  # recorrente: sempre reagendado
                "id": "r-recorrente", "phone": "5511", "message": "Remédio",
                "scheduled_at": (now - timedelta(days=10)).isoformat(),
                "timezone": "UTC", "is_recurring": True, "rrule": "CRON:0 9 * * *",
                "job_id": "r-recorrente",
            },
        ]
        with patch(
            "aisha.skills.reminder_store.get_all_pending_reminders",
            AsyncMock(return_value=rows),
        ), patch.object(reminder, "_schedule_job", AsyncMock(side_effect=lambda **kw: kw["reminder_id"])) as schedule, patch.object(
            reminder, "_send_whatsapp", AsyncMock()
        ) as send, patch.object(reminder, "mark_sent", AsyncMock()) as mark:
            restored = await reminder.restore_reminder_jobs(scheduler)

        self.assertEqual(restored, 2)
        scheduled_ids = {call.kwargs["reminder_id"] for call in schedule.await_args_list}
        self.assertEqual(scheduled_ids, {"r-futuro", "r-recorrente"})
        send.assert_awaited_once()
        self.assertIn("atrasado", send.await_args.args[1])
        marked_ids = {call.args[0] for call in mark.await_args_list}
        self.assertEqual(marked_ids, {"r-atrasado", "r-antigo"})

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
