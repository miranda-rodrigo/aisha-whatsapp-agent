"""Infraestrutura compartilhada para testes sem serviços externos."""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


TEST_ENV = {
    "WHATSAPP_TOKEN": "test-whatsapp-token",
    "WHATSAPP_PHONE_ID": "123456789",
    "WEBHOOK_VERIFY_TOKEN": "test-verify-token",
    "OPENAI_API_KEY": "sk-test",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-supabase-key",
    "USER_TIMEZONE": "America/Sao_Paulo",
    "BASE_URL": "https://aisha.test",
}


def configure_test_env() -> None:
    """Define as variáveis obrigatórias antes de importar ``aisha``."""
    for key, value in TEST_ENV.items():
        os.environ.setdefault(key, value)


def async_http_client(*responses):
    """Cria um AsyncClient fake com respostas sequenciais por método."""
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    client.aclose = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=context)
    if responses:
        client.get.side_effect = list(responses)
    return factory, client


def http_response(status_code=200, json_data=None, text="", content=b""):
    """Cria uma resposta HTTP mínima compatível com os módulos testados."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.text = text
    response.content = content
    if status_code >= 400:
        response.raise_for_status.side_effect = RuntimeError(f"HTTP {status_code}")
    else:
        response.raise_for_status.return_value = None
    return response


def namespace(**kwargs):
    """Atalho legível para objetos de resposta de SDKs."""
    return SimpleNamespace(**kwargs)


configure_test_env()
