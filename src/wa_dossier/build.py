"""Monta a conversa e gera o HTML. Nesta iteração, só o nível 0."""

from __future__ import annotations

from pathlib import Path

from .model import (
    build_conversation,
    conversation_path,
    load_conversation,
    merge_layers,
    save_conversation,
)
from .render_html import render_html


def output_dir_for(source: Path, output_root: Path) -> Path:
    return output_root / Path(source).stem


def build(source: Path, output_root: Path, *, nivel: int = 0, objetivo: str = "",
          me: str | None = None) -> Path:
    if nivel != 0:
        raise SystemExit(
            "Nesta iteração só existe o nível 0 (conversa legível, sem IA). "
            "Transcrição e comentários vêm na próxima."
        )
    source = source.expanduser().resolve()
    out_dir = output_dir_for(source, output_root)
    json_path = conversation_path(out_dir)
    previous = load_conversation(json_path) if json_path.exists() else None
    conv = merge_layers(build_conversation(source, objetivo), previous)
    conv["nivel"] = 0
    if objetivo:
        conv["objetivo"] = objetivo
    save_conversation(conv, json_path)
    html_path = render_html(conv, out_dir / "conversa.html", me=me)
    print(f"HTML: {html_path}")
    print(f"JSON: {json_path}")
    return html_path
