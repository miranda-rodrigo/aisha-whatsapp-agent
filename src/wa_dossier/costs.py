"""Registro de cada chamada de API em output/<chat>/custos.json."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from .config import estimate_cost

_lock = threading.Lock()


def costs_path(out_dir: Path) -> Path:
    return out_dir / "custos.json"


def record(out_dir: Path, *, etapa: str, model: str, input_tokens: int = 0,
           output_tokens: int = 0, audio_seconds: float | None = None,
           item: str = "") -> dict:
    cost = estimate_cost(model, input_tokens, output_tokens, audio_seconds)
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "etapa": etapa,
        "model": model,
        "item": item,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "audio_seconds": round(audio_seconds, 2) if audio_seconds else None,
        "cost_usd": None if cost is None else round(cost, 6),
    }
    path = costs_path(out_dir)
    with _lock:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        data.append(entry)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def summarize(out_dir: Path) -> str:
    path = costs_path(out_dir)
    if not path.exists():
        return "Nenhuma chamada de API registrada."
    data = json.loads(path.read_text(encoding="utf-8"))
    by_etapa: dict[str, dict] = {}
    total = 0.0
    known = True
    for entry in data:
        bucket = by_etapa.setdefault(entry["etapa"], {"calls": 0, "cost": 0.0, "audio": 0.0})
        bucket["calls"] += 1
        bucket["audio"] += entry.get("audio_seconds") or 0
        if entry.get("cost_usd") is None:
            known = False
        else:
            bucket["cost"] += entry["cost_usd"]
            total += entry["cost_usd"]
    lines = [f"Chamadas de API: {len(data)}"]
    for etapa, bucket in by_etapa.items():
        audio = f", {bucket['audio'] / 60:.1f} min de áudio" if bucket["audio"] else ""
        lines.append(f"  {etapa}: {bucket['calls']} chamadas, US$ {bucket['cost']:.4f}{audio}")
    lines.append(f"Total estimado: US$ {total:.4f}" + ("" if known else " (parcial, falta preço de algum modelo)"))
    return "\n".join(lines)


def usage_tokens(usage) -> tuple[int, int]:
    """Lê tokens de um objeto de usage da OpenAI, em qualquer um dos formatos."""
    if usage is None:
        return 0, 0
    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    elif hasattr(usage, "dict"):
        usage = usage.dict()
    elif not isinstance(usage, dict):
        usage = {
            "input_tokens": getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or getattr(usage, "completion_tokens", 0) or 0,
        }
    inp = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
    out = usage.get("output_tokens") or usage.get("completion_tokens") or 0
    return int(inp or 0), int(out or 0)
