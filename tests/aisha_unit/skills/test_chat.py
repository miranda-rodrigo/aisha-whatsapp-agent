"""Testes unitários da skill de chat."""

import base64
import unittest
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import configure_test_env, namespace

configure_test_env()

from aisha.skills import chat


def text_response(text="Olá", response_id="resp-1"):
    return namespace(
        id=response_id,
        output=[
            namespace(
                type="message",
                content=[namespace(type="output_text", text=text)],
            )
        ],
    )


class ChatPureTests(unittest.TestCase):
    def test_build_instructions_inclui_perfil(self):
        with patch.object(chat, "_now_str", return_value="domingo, 16 de agosto de 2026, 07:00"):
            result = chat._build_instructions(
                "Base",
                {
                    "timezone": "America/Fortaleza",
                    "personal_context": "Programador Python",
                    "language": "português",
                },
            )
        self.assertIn("America/Fortaleza", result)
        self.assertIn("Programador Python", result)
        self.assertIn("Idioma preferido do usuário: português", result)

    def test_wants_new_session_delega_para_routing(self):
        with patch.object(chat, "_wants_new_session", return_value=True) as delegate:
            self.assertTrue(chat.wants_new_session("novo assunto"))
        delegate.assert_called_once_with("novo assunto")


class ChatAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_classificadores_normalizam_e_usam_fallback(self):
        response = namespace(
            choices=[namespace(message=namespace(content="scheduled-task extra"))]
        )
        with patch.object(
            chat._client.chat.completions, "create", AsyncMock(return_value=response)
        ):
            self.assertEqual(await chat.classify("agende"), "SCHEDULED_TASK")

        invalid = namespace(choices=[namespace(message=namespace(content="desconhecido"))])
        with patch.object(
            chat._client.chat.completions, "create", AsyncMock(return_value=invalid)
        ):
            self.assertEqual(await chat.classify("texto"), "COMPLEX")
            self.assertEqual(
                await chat.classify_pending_response("texto", "aguardando horário"),
                "CONTINUE",
            )

    async def test_chat_obtem_perfil_e_delega_rota(self):
        with patch("aisha.user_profile.get_profile", AsyncMock(return_value={"language": "pt"})), patch.object(
            chat, "classify", AsyncMock(return_value="SIMPLE")
        ), patch.object(chat, "_chat_simple", AsyncMock(return_value=chat.ChatResult(text="ok"))) as simple:
            result = await chat.chat("oi", phone="5511")
        self.assertEqual(result.text, "ok")
        simple.assert_awaited_once_with("oi", None, {"language": "pt"})

    async def test_chat_simple_monta_contrato_e_extrai_texto(self):
        with patch.object(
            chat._client.responses, "create", AsyncMock(return_value=text_response("Tudo bem"))
        ) as create:
            result = await chat._chat_simple("oi", "resp-anterior", {"language": "português"})
        self.assertEqual(result, chat.ChatResult(text="Tudo bem", response_id="resp-1"))
        self.assertEqual(create.await_args.kwargs["previous_response_id"], "resp-anterior")
        self.assertEqual(create.await_args.kwargs["model"], "gpt-5.6-sol")
        self.assertEqual(create.await_args.kwargs["service_tier"], "fast")

    async def test_chat_complex_extrai_texto_e_imagem(self):
        image = b"imagem"
        response = text_response("Pronto")
        response.output.append(
            namespace(type="image_generation_call", result=base64.b64encode(image).decode())
        )
        with patch.object(
            chat._client.responses, "create", AsyncMock(return_value=response)
        ) as create:
            result = await chat._chat_complex("crie", None)
        self.assertEqual(result.text, "Pronto")
        self.assertEqual(result.image_bytes, image)
        self.assertEqual(
            create.await_args.kwargs["tools"],
            [{"type": "web_search"}, {"type": "image_generation"}],
        )
        self.assertEqual(create.await_args.kwargs["model"], "gpt-5.6-sol")
        self.assertEqual(create.await_args.kwargs["service_tier"], "fast")

    async def test_chat_com_imagem_codifica_entrada(self):
        response = text_response("Editada")
        with patch.object(
            chat._client.responses, "create", AsyncMock(return_value=response)
        ) as create:
            result = await chat.chat_with_image("melhore", b"abc", "image/png")
        image_url = create.await_args.kwargs["input"][0]["content"][0]["image_url"]
        self.assertEqual(image_url, "data:image/png;base64,YWJj")
        self.assertEqual(result.text, "Editada")

    async def test_documento_e_webpage_preservam_contexto(self):
        with patch.object(
            chat._client.responses, "create", AsyncMock(return_value=text_response("Resumo"))
        ) as create:
            result = await chat.chat_with_document("conteúdo", "resuma", "prev")
        self.assertEqual(result.text, "Resumo")
        self.assertIn("INSTRUÇÃO: resuma", create.await_args.kwargs["input"])
        self.assertEqual(create.await_args.kwargs["previous_response_id"], "prev")

        with patch.object(
            chat._client.responses, "create", AsyncMock(return_value=text_response("Página"))
        ) as create:
            result = await chat.chat_with_webpage("texto", "https://example.com", None)
        self.assertEqual(result.text, "Página")
        self.assertIn("URL: https://example.com", create.await_args.kwargs["input"])


if __name__ == "__main__":
    unittest.main()
