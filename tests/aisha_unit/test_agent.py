"""Testes unitários do loop agentic, sem chamadas ao OpenAI."""

import base64
import unittest
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import namespace

import aisha.agent as agent


def message_response(response_id: str, *texts: str, image: bytes | None = None):
    output = []
    if texts:
        output.append(
            namespace(
                type="message",
                content=[
                    namespace(type="output_text", text=text)
                    for text in texts
                ],
            )
        )
    if image is not None:
        output.append(
            namespace(
                type="image_generation_call",
                result=base64.b64encode(image).decode(),
            )
        )
    return namespace(id=response_id, output=output)


def tool_response(response_id: str, name: str = "web_search"):
    return namespace(
        id=response_id,
        output=[
            namespace(
                type="function_call",
                name=name,
                arguments='{"query":"agora"}',
                call_id=f"call-{response_id}",
            )
        ],
    )


class ParseResponseTests(unittest.TestCase):
    def test_parse_response_combines_text_and_decodes_image(self):
        response = message_response("resp-1", "primeira", "segunda", image=b"png")

        text, image = agent._parse_response(response)

        self.assertEqual(text, "primeira\nsegunda")
        self.assertEqual(image, b"png")

    def test_parse_response_returns_none_without_supported_output(self):
        response = namespace(
            id="resp-1",
            output=[namespace(type="reasoning", content=[])],
        )

        self.assertEqual(agent._parse_response(response), (None, None))


class SystemPromptTests(unittest.TestCase):
    def test_maps_use_draw_radius_map_not_image_generation(self):
        prompt = agent._build_system_prompt(None, "America/Sao_Paulo")
        self.assertIn("draw_radius_map", prompt)
        self.assertIn("NUNCA use image_generation para mapas", prompt)
        self.assertIn("area_label", prompt)
        self.assertIn("temporariamente sem configuração", prompt)


class AgentLoopTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.create = AsyncMock()
        self.client_patch = patch.object(agent._client.responses, "create", self.create)
        self.client_patch.start()

    async def asyncTearDown(self):
        self.client_patch.stop()

    async def test_fast_path_uses_profile_timezone_and_previous_response(self):
        response = message_response("fast-1", "Oi!")
        self.create.return_value = response
        profile = {"timezone": "Europe/Lisbon", "language": "pt"}

        with patch("aisha.user_profile.get_profile", AsyncMock(return_value=profile)):
            result = await agent.run_fast_path(
                "oi",
                previous_response_id="previous-1",
                phone="5511",
            )

        kwargs = self.create.await_args.kwargs
        self.assertEqual(kwargs["model"], agent.FAST_MODEL)
        self.assertEqual(kwargs["input"], "oi")
        self.assertEqual(kwargs["previous_response_id"], "previous-1")
        self.assertIn("Europe/Lisbon", kwargs["instructions"])
        self.assertEqual(result.text, "Oi!")
        self.assertEqual(result.response_id, "fast-1")
        self.assertEqual(result.iterations, 1)

    async def test_agent_executes_tool_then_returns_final_response(self):
        self.create.side_effect = [
            tool_response("step-1", "web_search"),
            message_response("step-2", "resultado", image=b"image"),
        ]

        with patch.object(
            agent,
            "execute_tool",
            AsyncMock(return_value='{"ok":true}'),
        ) as execute:
            result = await agent.run_agent(
                "pesquise",
                previous_response_id="previous-1",
                scheduler="scheduler",
            )

        execute.assert_awaited_once()
        self.assertEqual(execute.await_args.args[:2], ("web_search", '{"query":"agora"}'))
        second_kwargs = self.create.await_args_list[1].kwargs
        self.assertEqual(second_kwargs["previous_response_id"], "step-1")
        self.assertEqual(
            second_kwargs["input"],
            [
                {
                    "type": "function_call_output",
                    "call_id": "call-step-1",
                    "output": '{"ok":true}',
                }
            ],
        )
        self.assertEqual(result.text, "resultado")
        self.assertEqual(result.image_bytes, b"image")
        self.assertEqual(result.tools_called, ["web_search"])
        self.assertEqual(result.iterations, 2)
        self.assertEqual(result.response_id, "step-2")

    async def test_agent_stops_at_iteration_limit(self):
        responses = [
            tool_response(f"step-{number}", "get_weather")
            for number in range(1, agent._MAX_ITERATIONS + 1)
        ]
        self.create.side_effect = responses

        with patch.object(
            agent,
            "execute_tool",
            AsyncMock(return_value="ok"),
        ) as execute:
            result = await agent.run_agent("continue usando ferramentas")

        self.assertEqual(self.create.await_count, agent._MAX_ITERATIONS)
        self.assertEqual(execute.await_count, agent._MAX_ITERATIONS)
        self.assertEqual(result.iterations, agent._MAX_ITERATIONS)
        self.assertEqual(result.response_id, f"step-{agent._MAX_ITERATIONS}")
        self.assertEqual(
            result.tools_called,
            ["get_weather"] * agent._MAX_ITERATIONS,
        )
        self.assertIsNone(result.text)

    async def test_agent_attaches_radius_map_image_from_store(self):
        self.create.side_effect = [
            tool_response("step-1", "draw_radius_map"),
            message_response("step-2", "mapa pronto"),
        ]

        with patch.object(
            agent,
            "execute_tool",
            AsyncMock(return_value='{"status":"ok"}'),
        ), patch(
            "aisha.skills.radius_map.pop_map_image",
            return_value=b"map-png",
        ) as pop, patch(
            "aisha.user_profile.get_profile",
            AsyncMock(return_value=None),
        ), patch(
            "aisha.skills.reminder_store.get_reminders",
            AsyncMock(return_value=[]),
        ), patch(
            "aisha.skills.memory_store.search_memories",
            AsyncMock(return_value=[]),
        ):
            result = await agent.run_agent(
                "mapa de 2 km em Fortaleza",
                phone="5511",
            )

        pop.assert_called_once_with("5511")
        self.assertEqual(result.image_bytes, b"map-png")
        self.assertEqual(result.text, "mapa pronto")
        self.assertEqual(result.tools_called, ["draw_radius_map"])


if __name__ == "__main__":
    unittest.main()
