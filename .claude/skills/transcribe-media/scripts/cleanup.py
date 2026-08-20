#!/usr/bin/env python3
"""Deterministic transcript cleanup. Never modifies the source/raw file."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Import caption parser without requiring a package install.
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from transcribe import _looks_like_captions, parse_caption_text  # noqa: E402

# Obvious filled pauses only. Do not strip real Portuguese words (tipo, né, então)
# or the article "um" before a word. "um," / "umm" / "uh" still count as pauses.
_FILLER_RE = re.compile(
    r"(?:(?<=^)|(?<=\s))(?:uh+|umm+|uhm+|hã+|hmm+|é{3,}|ahm+)(?=\s|$|[.,!?…])",
    re.IGNORECASE,
)
_UM_PAUSE_RE = re.compile(
    r"(?:(?<=^)|(?<=\s))um(?=[.,!?…])",
    re.IGNORECASE,
)
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def cleanup_text(text: str) -> str:
    """Normalize spacing and drop obvious filler pauses. Conservative."""
    if _looks_like_captions(text):
        text = parse_caption_text(text)
    cleaned = _FILLER_RE.sub("", text)
    cleaned = _UM_PAUSE_RE.sub("", cleaned)
    cleaned = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", cleaned)
    cleaned = "\n".join(_MULTI_SPACE_RE.sub(" ", line).strip() for line in cleaned.splitlines())
    cleaned = _MULTI_BLANK_RE.sub("\n\n", cleaned)
    return cleaned.strip() + ("\n" if cleaned.strip() else "")


def cleanup_file(src: str | Path, dst: str | Path) -> str:
    """Read src, write cleaned text to dst, leave src bytes unchanged."""
    source = Path(src)
    dest = Path(dst)
    original = source.read_bytes()
    text = original.decode("utf-8", errors="replace")
    cleaned = cleanup_text(text)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(cleaned, encoding="utf-8")
    if source.read_bytes() != original:
        raise RuntimeError(f"cleanup_file altered the source file: {source}")
    return cleaned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Limpa transcrição sem IA. Não altera o arquivo de origem."
    )
    parser.add_argument("source", help="raw.txt, .srt/.vtt, ou diretório com raw.txt")
    parser.add_argument(
        "--out",
        "-o",
        help="Arquivo de saída (padrão: <dir>/cleaned.txt ao lado do raw)",
    )
    args = parser.parse_args(argv)
    source = Path(args.source)
    if source.is_dir():
        source = source / "raw.txt"
    if not source.is_file():
        print(f"ERRO: arquivo não encontrado: {source}", file=sys.stderr)
        return 1
    dest = Path(args.out) if args.out else source.parent / "cleaned.txt"
    try:
        cleanup_file(source, dest)
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
