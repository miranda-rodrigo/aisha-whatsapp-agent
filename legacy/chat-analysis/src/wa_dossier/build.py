"""Pipeline: monta a conversa, aplica os níveis pedidos e gera HTML + Markdown."""

from __future__ import annotations

from pathlib import Path

from . import costs
from .model import (
    build_conversation,
    conversation_path,
    load_conversation,
    merge_layers,
    save_conversation,
)
from .render_html import render_html
from .render_md import render_md


def output_dir_for(source: Path, output_root: Path) -> Path:
    return output_root / Path(source).stem


def build(source: Path, output_root: Path, *, nivel: int = 0, objetivo: str = "",
          me: str | None = None, limit: int | None = None) -> Path:
    source = source.expanduser().resolve()
    out_dir = output_dir_for(source, output_root)
    json_path = conversation_path(out_dir)
    previous = load_conversation(json_path) if json_path.exists() else None
    conv = merge_layers(build_conversation(source, objetivo), previous)
    if objetivo:
        conv["objetivo"] = objetivo
    save_conversation(conv, json_path)

    if nivel >= 1:
        from .transcribe import transcribe_conversation
        print("Nível 1: transcrevendo áudios...")
        n = transcribe_conversation(conv, out_dir, limit=limit)
        print(f"  {n} áudios transcritos nesta rodada.")
        save_conversation(conv, json_path)
    if nivel >= 2:
        from .annotate import annotate_conversation
        print("Nível 2: comentando mídias...")
        n = annotate_conversation(conv, out_dir, limit=limit)
        print(f"  {n} mídias comentadas nesta rodada.")
        save_conversation(conv, json_path)
    if nivel >= 3:
        from .analyze import analyze_conversation
        print("Nível 3: analisando a conversa...")
        analyze_conversation(conv, out_dir)
        save_conversation(conv, json_path)

    conv["nivel"] = max(nivel, conv.get("nivel") or 0)
    save_conversation(conv, json_path)

    html_path = render_html(conv, out_dir / "conversa.html", me=me)
    md_path = render_md(conv, out_dir)
    print(f"HTML: {html_path}")
    print(f"Markdown p/ IA: {md_path}")
    print(f"JSON: {json_path}")
    print(costs.summarize(out_dir))
    return html_path
