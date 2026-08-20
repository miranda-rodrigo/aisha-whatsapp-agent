#!/usr/bin/env python3
"""Melhoria editorial com gpt-5.6-luna (reasoning none). Não altera o bruto."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import chat  # noqa: E402


def _prompt_path(prompt_file: str | None) -> Path:
    if prompt_file:
        return Path(prompt_file)
    return _SCRIPTS.parent / "references" / "refine-prompt.md"


def improve(text: str, prompt_file: str | None) -> dict:
    raw = (text or "").strip()
    if not raw:
        chat.fail("Texto bruto vazio; não há o que melhorar.")
    prompt_path = _prompt_path(prompt_file)
    if not prompt_path.is_file():
        chat.fail(f"Prompt editorial não encontrado: {prompt_path}")
    system = prompt_path.read_text(encoding="utf-8")
    chunks = chat.chunk_text(raw)

    def _user(index: int, chunk: str, total: int) -> str:
        if total == 1:
            return chunk
        return (
            f"Parte {index + 1} de {total} da transcrição bruta. "
            f"Edite só este trecho, sem resumir.\n\n{chunk}"
        )

    pieces = chat.map_chat_chunks(system, chunks, _user)
    improved = "\n\n".join(pieces).strip()
    return {
        "ok": True,
        "text": improved,
        "model": chat.CHAT_MODEL,
        "chunk_count": len(chunks),
        "method": "improve",
    }


def improve_file(input_path: Path, output_path: Path, prompt_file: str | None) -> dict:
    if not input_path.is_file():
        chat.fail(f"Arquivo não encontrado: {input_path}")
    if input_path.resolve() == output_path.resolve():
        chat.fail("Recusa: não vou sobrescrever o bruto. Use --out em outro arquivo.")
    raw_bytes = input_path.read_bytes()
    payload = improve(input_path.read_text(encoding="utf-8", errors="replace"), prompt_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = payload["text"]
    output_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    if input_path.read_bytes() != raw_bytes:
        chat.fail("O arquivo bruto mudou durante a melhoria; abortando.")
    payload["out"] = str(output_path)
    payload["raw"] = str(input_path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Edita o bruto com gpt-5.6-luna (reasoning none). Não sobrescreve o raw."
    )
    parser.add_argument("input", nargs="?", help="Arquivo bruto (raw.txt)")
    parser.add_argument("--input", "-i", dest="input_opt")
    parser.add_argument("--text")
    parser.add_argument("--out", "-o", help="Arquivo de saída (improved.txt)")
    parser.add_argument("--prompt-file", default=None)
    args = parser.parse_args(argv)
    source = args.input_opt or args.input
    try:
        if args.text is not None:
            payload = improve(args.text, args.prompt_file)
            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                text = payload["text"]
                out.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
                payload["out"] = str(out)
        elif source:
            in_path = Path(source)
            out_path = Path(args.out) if args.out else in_path.with_name("improved.txt")
            payload = improve_file(in_path, out_path, args.prompt_file)
        else:
            chat.fail("Informe o arquivo de entrada, --input ou --text.")
    except SystemExit as exc:
        return int(exc.code or 1)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
