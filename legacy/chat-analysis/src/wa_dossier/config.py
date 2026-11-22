"""Leitura do .env e preços usados para estimar custo. Sem dependências externas."""

from __future__ import annotations

import os
from pathlib import Path

# Preços em USD, conferidos na página oficial da OpenAI em 31/10/2026.
# gpt-4o-mini-transcribe consta como deprecated, mas segue na tabela a US$ 0,003/min.
# O substituto listado, gpt-transcribe, custa US$ 0,0045/min. O padrão continua o mini
# enquanto a API aceitar; o código troca para gpt-transcribe se o modelo for recusado.
# gpt-4o-mini: US$ 0,15 / US$ 0,60 por 1M tokens (entrada / saída). Aceita imagem.
PRODUCT_NAME = "what_an_analysis"

STT_MODEL = "gpt-4o-mini-transcribe"
STT_FALLBACK = "gpt-transcribe"
LLM_MODEL = "gpt-4o-mini"

PRICES_PER_MILLION = {
    "gpt-4o-mini-transcribe": {"input": 1.25, "output": 5.00},
    "gpt-4o-transcribe": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-5-mini": {"input": 0.25, "output": 2.00},
}

PRICE_PER_MINUTE = {
    "gpt-4o-mini-transcribe": 0.003,
    "gpt-4o-transcribe": 0.006,
    "gpt-transcribe": 0.0045,
    "whisper-1": 0.006,
}


def load_env(path: Path | None = None) -> None:
    """Coloca variáveis do .env no ambiente, sem sobrescrever as que já existem."""
    env_path = path or Path(".env")
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def estimate_cost(model: str, input_tokens: int = 0, output_tokens: int = 0,
                  audio_seconds: float | None = None) -> float | None:
    """Estima USD. Prefere tokens quando o modelo tem tabela; senão, minutos de áudio."""
    rates = PRICES_PER_MILLION.get(model)
    if rates and (input_tokens or output_tokens):
        return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
    per_min = PRICE_PER_MINUTE.get(model)
    if per_min is not None and audio_seconds:
        return audio_seconds / 60 * per_min
    return None
