"""Contratos, validação e delegação dos wrappers de tools."""

import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from tests.aisha_unit._helpers import configure_test_env

configure_test_env()

from aisha import tools
from aisha.tools import memory, profile, reminder, scheduled_task, video_download, webpage, youtube
from aisha.tools import radius_map as radius_map_tool


def decoded(value: str) -> dict:
    return json.loads(value)


class ToolTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        scheduler = MagicMock()
        scheduler.remove_schedule = AsyncMock()
        self.ctx = tools.ToolContext(
            phone="5511999999999",
            scheduler=scheduler,
            user_tz="America/Sao_Paulo",
            base_url="https://aisha.test",
        )


class DispatcherTests(ToolTestCase):
    def test_definicoes_tem_nomes_unicos_e_schema_fechado(self):
        definitions = [item for item in tools.TOOL_DEFINITIONS if item["type"] == "function"]
        names = [item["name"] for item in definitions]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(tools._DISPATCH))
        self.assertTrue(
            all(item["parameters"]["additionalProperties"] is False for item in definitions)
        )

    async def test_dispatch_valida_nome_json_e_converte_excecao(self):
        self.assertIn("Unknown tool", decoded(await tools.execute_tool("inexistente", "{}", self.ctx))["error"])

        handler = AsyncMock(return_value='{"status": "ok"}')
        with patch.dict(tools._DISPATCH, {"fake": handler}):
            result = await tools.execute_tool("fake", '{"x": 1}', self.ctx)
        self.assertEqual(decoded(result), {"status": "ok"})
        handler.assert_awaited_once_with({"x": 1}, self.ctx)

        with patch.dict(tools._DISPATCH, {"fake": AsyncMock(side_effect=RuntimeError("falhou"))}):
            result = await tools.execute_tool("fake", "{}", self.ctx)
        self.assertEqual(decoded(result), {"error": "falhou"})


class SimpleWrapperTests(ToolTestCase):
    async def test_youtube_valida_url_e_delega(self):
        self.assertIn("error", decoded(await youtube.tool_analyze_youtube_video({}, self.ctx)))
        analysis = SimpleNamespace(
            text="análise",
            download_token=None,
            download_link=None,
            filename=None,
            is_long=False,
        )
        with patch("aisha.skills.youtube.analyze_video", AsyncMock(return_value=analysis)) as analyze:
            result = decoded(
                await youtube.tool_analyze_youtube_video(
                    {"url": "https://youtu.be/abc", "instruction": "resuma"}, self.ctx
                )
            )
        self.assertEqual(result, {"analysis": "análise"})
        analyze.assert_awaited_once_with("https://youtu.be/abc", "resuma")

    async def test_webpage_valida_url_e_aplica_instrucao_padrao(self):
        self.assertIn("error", decoded(await webpage.tool_read_webpage({}, self.ctx)))
        with patch("aisha.skills.webpage.fetch_page", AsyncMock(return_value="# Conteúdo")) as fetch:
            result = decoded(
                await webpage.tool_read_webpage({"url": "https://example.com"}, self.ctx)
            )
        self.assertEqual(result["content"], "# Conteúdo")
        self.assertIn("resumo", result["instruction"])
        fetch.assert_awaited_once_with("https://example.com")

    async def test_download_valida_url_e_monta_link(self):
        self.assertIn("error", decoded(await video_download.tool_download_video({}, self.ctx)))
        with patch(
            "aisha.skills.video_download.download_video",
            AsyncMock(return_value=("token-1", "video.mp4")),
        ) as download:
            result = decoded(
                await video_download.tool_download_video({"url": "https://youtu.be/abc"}, self.ctx)
            )
        self.assertEqual(result["download_link"], "https://aisha.test/download/token-1")
        self.assertEqual(result["filename"], "video.mp4")
        download.assert_awaited_once_with("https://youtu.be/abc")

    async def test_draw_radius_map_delega(self):
        with patch(
            "aisha.skills.radius_map.build_radius_map",
            AsyncMock(return_value={"status": "ok", "lat": -3.73}),
        ) as build:
            result = decoded(
                await radius_map_tool.tool_draw_radius_map(
                    {"address": "Fortaleza", "radius": 2, "unit": "km"},
                    self.ctx,
                )
            )
        self.assertEqual(result["status"], "ok")
        build.assert_awaited_once_with(
            phone=self.ctx.phone,
            address="Fortaleza",
            latitude=None,
            longitude=None,
            radius=2,
            unit="km",
        )


class MemoryToolTests(ToolTestCase):
    async def test_save_memory_normaliza_e_delega(self):
        self.assertIn("error", decoded(await memory.tool_save_memory({"content": "  "}, self.ctx)))
        with patch(
            "aisha.skills.memory_store.save_memory",
            AsyncMock(return_value={"id": "m1"}),
        ) as save:
            result = decoded(await memory.tool_save_memory({"content": "  Gosta de café  "}, self.ctx))
        self.assertEqual(result, {"status": "saved", "id": "m1", "content": "Gosta de café"})
        save.assert_awaited_once_with(self.ctx.phone, "Gosta de café")

    async def test_search_list_e_forget_memory(self):
        self.assertIn("error", decoded(await memory.tool_search_memory({}, self.ctx)))
        with patch(
            "aisha.skills.memory_store.search_memories",
            AsyncMock(return_value=[{"id": "m1"}]),
        ) as search:
            result = decoded(
                await memory.tool_search_memory({"query": "café", "limit": "2"}, self.ctx)
            )
        self.assertEqual(result["results"], [{"id": "m1"}])
        search.assert_awaited_once_with(self.ctx.phone, "café", limit=2)

        rows = [{"id": "m1", "content": "Café", "created_at": "hoje", "extra": True}]
        with patch("aisha.skills.memory_store.list_memories", AsyncMock(return_value=rows)):
            result = decoded(await memory.tool_list_memories({}, self.ctx))
        self.assertEqual(result["count"], 1)
        self.assertNotIn("extra", result["memories"][0])

        self.assertIn("error", decoded(await memory.tool_forget_memory({}, self.ctx)))
        with patch(
            "aisha.skills.memory_store.delete_memory", AsyncMock(return_value=1)
        ) as delete:
            result = decoded(
                await memory.tool_forget_memory({"memory_id": "m1"}, self.ctx)
            )
        self.assertEqual(result, {"status": "deleted", "count": 1})
        delete.assert_awaited_once_with(self.ctx.phone, memory_id="m1", content_query=None)


class ProfileToolTests(ToolTestCase):
    async def test_contexto_e_idioma_validam_e_persistem(self):
        self.assertIn("error", decoded(await profile.tool_set_personal_context({}, self.ctx)))
        with patch(
            "aisha.user_profile.get_profile",
            AsyncMock(return_value={"personal_context": "Existente"}),
        ), patch("aisha.user_profile.upsert_context", AsyncMock()) as upsert:
            result = decoded(
                await profile.tool_set_personal_context({"context": "Novo"}, self.ctx)
            )
        self.assertEqual(result["context_length"], len("Existente\nNovo"))
        upsert.assert_awaited_once_with(self.ctx.phone, "Existente\nNovo")

        self.assertIn("error", decoded(await profile.tool_set_language({}, self.ctx)))
        with patch("aisha.user_profile.upsert_language", AsyncMock()) as language:
            result = decoded(await profile.tool_set_language({"language": "english"}, self.ctx))
        self.assertEqual(result["language"], "english")
        language.assert_awaited_once_with(self.ctx.phone, "english")

    async def test_get_profile_agrega_dependencias_e_tolera_memoria_indisponivel(self):
        reminder_rows = [
            {
                "message": "Consulta",
                "scheduled_at": "2030-01-01T12:00:00+00:00",
                "is_recurring": False,
            }
        ]
        with patch(
            "aisha.user_profile.get_profile",
            AsyncMock(return_value={"language": "pt", "timezone": "UTC"}),
        ), patch(
            "aisha.skills.reminder_store.get_reminders", AsyncMock(return_value=reminder_rows)
        ), patch(
            "aisha.skills.scheduled_task_store.get_tasks",
            AsyncMock(return_value=[{"name": "Mercado", "cron_expression": "0 8 * * *"}]),
        ), patch(
            "aisha.skills.memory_store.list_memories",
            AsyncMock(side_effect=RuntimeError("offline")),
        ):
            result = decoded(await profile.tool_get_my_profile({}, self.ctx))
        self.assertEqual(result["timezone"], "UTC")
        self.assertEqual(result["active_reminders"][0]["message"], "Consulta")
        self.assertEqual(result["scheduled_tasks"][0]["name"], "Mercado")
        self.assertEqual(result["memories"], [])


class ReminderToolTests(ToolTestCase):
    async def test_create_valida_argumentos(self):
        result = decoded(await reminder.tool_create_reminder({"message": "Consulta"}, self.ctx))
        self.assertIn("datetime_iso ou cron_expression", result["error"])

    async def test_create_delega_persistencia_e_agendamento(self):
        event_at = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
        with patch(
            "aisha.skills.reminder._parse_dt_iso", return_value=event_at
        ), patch(
            "aisha.skills.reminder._fmt_local", return_value="01/01 às 09:00"
        ), patch(
            "aisha.skills.reminder._gcal_link", return_value="https://calendar.test"
        ), patch(
            "aisha.skills.reminder._schedule_job", AsyncMock(return_value="j1")
        ) as schedule, patch(
            "aisha.skills.reminder_store.save_reminder", AsyncMock(return_value="r1")
        ) as save, patch(
            "aisha.skills.reminder_store.update_job_id", AsyncMock()
        ) as update:
            result = decoded(
                await reminder.tool_create_reminder(
                    {
                        "message": "Consulta",
                        "datetime_iso": "2030-01-01T09:00:00",
                        "lead_minutes": 20,
                    },
                    self.ctx,
                )
            )
        self.assertEqual(result["status"], "created")
        self.assertEqual(save.await_args.args[0].phone, self.ctx.phone)
        self.assertEqual(schedule.await_args.kwargs["lead_minutes"], 20)
        update.assert_awaited_once_with("r1", "j1")

    async def test_list_edit_e_cancel_validam_indice(self):
        with patch("aisha.skills.reminder_store.get_reminders", AsyncMock(return_value=[])):
            self.assertEqual(
                decoded(await reminder.tool_list_reminders({}, self.ctx))["reminders"], []
            )
            self.assertIn(
                "error",
                decoded(await reminder.tool_edit_reminder({"reminder_number": 1}, self.ctx)),
            )
            self.assertIn(
                "error",
                decoded(await reminder.tool_cancel_reminder({"reminder_number": 1}, self.ctx)),
            )

        rows = [{"id": "r1", "message": "Consulta", "job_id": "j1"}]
        with patch(
            "aisha.skills.reminder_store.get_reminders", AsyncMock(return_value=rows)
        ), patch(
            "aisha.skills.reminder_store.cancel_reminder", AsyncMock()
        ) as cancel:
            result = decoded(
                await reminder.tool_cancel_reminder({"reminder_number": 1}, self.ctx)
            )
        self.assertEqual(result["status"], "cancelled")
        cancel.assert_awaited_once_with("r1")
        self.ctx.scheduler.remove_schedule.assert_awaited_once_with("j1")


class ScheduledTaskToolTests(ToolTestCase):
    async def test_create_valida_e_delega(self):
        self.assertIn(
            "error",
            decoded(await scheduled_task.tool_create_scheduled_task({}, self.ctx)),
        )
        with patch("aisha.skills.scheduled_task._parse_cron"), patch(
            "aisha.skills.scheduled_task._schedule_job", AsyncMock(return_value="j1")
        ) as schedule, patch(
            "aisha.skills.scheduled_task_store.save_task", AsyncMock(return_value="t1")
        ) as save, patch(
            "aisha.skills.scheduled_task_store.update_job_id", AsyncMock()
        ) as update:
            result = decoded(
                await scheduled_task.tool_create_scheduled_task(
                    {
                        "name": "Mercado",
                        "prompt": "Resuma o mercado",
                        "cron_expression": "0 8 * * *",
                    },
                    self.ctx,
                )
            )
        self.assertEqual(result["status"], "created")
        self.assertEqual(save.await_args.args[0].name, "Mercado")
        schedule.assert_awaited_once()
        update.assert_awaited_once_with("t1", "j1")

    async def test_list_e_cancel_delegam(self):
        rows = [
            {
                "id": "t1",
                "name": "Mercado",
                "prompt": "Resumo financeiro",
                "cron_expression": "0 8 * * *",
                "job_id": "j1",
            }
        ]
        with patch(
            "aisha.skills.scheduled_task_store.get_tasks", AsyncMock(return_value=rows)
        ):
            result = decoded(await scheduled_task.tool_list_scheduled_tasks({}, self.ctx))
        self.assertEqual(result["tasks"][0]["number"], 1)
        self.assertEqual(result["tasks"][0]["prompt_preview"], "Resumo financeiro")

        with patch(
            "aisha.skills.scheduled_task_store.get_tasks", AsyncMock(return_value=rows)
        ), patch(
            "aisha.skills.scheduled_task_store.deactivate_task", AsyncMock()
        ) as deactivate:
            result = decoded(
                await scheduled_task.tool_cancel_scheduled_task({"task_number": 1}, self.ctx)
            )
        self.assertEqual(result["status"], "cancelled")
        deactivate.assert_awaited_once_with("t1")
        self.ctx.scheduler.remove_schedule.assert_awaited_once_with("j1")


if __name__ == "__main__":
    unittest.main()
