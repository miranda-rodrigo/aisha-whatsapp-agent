"""Abertura da exportação (.zip ou pasta) e localização do chat e das mídias."""

from __future__ import annotations

import zipfile
from pathlib import Path


def extract_export(source: Path, work_root: Path | None = None) -> Path:
    """Garante uma pasta com o conteúdo da exportação.

    Se `source` for um .zip, extrai para `<work_root>/<nome-do-zip>/` (padrão:
    `data/_extracted/` ao lado do zip) e reaproveita extração anterior se existir.
    Se já for uma pasta, devolve a própria.
    """
    source = source.expanduser().resolve()
    if source.is_dir():
        return source
    if not zipfile.is_zipfile(source):
        raise ValueError(f"Não é um .zip nem uma pasta: {source}")

    root = work_root or source.parent / "_extracted"
    dest = root / source.stem
    if dest.exists() and any(dest.iterdir()):
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as zf:
        zf.extractall(dest)
    return dest


def find_chat_txt(folder: Path) -> Path:
    """Localiza o arquivo de texto do chat dentro da exportação."""
    candidates = sorted(folder.rglob("*.txt"))
    if not candidates:
        raise FileNotFoundError(f"Nenhum .txt encontrado em {folder}")
    # iPhone usa `_chat.txt`; Android costuma usar `Conversa do WhatsApp com X.txt`.
    for c in candidates:
        if c.name == "_chat.txt":
            return c
    # Senão, o maior .txt é quase certamente o chat.
    return max(candidates, key=lambda p: p.stat().st_size)


def list_media_files(folder: Path, chat_txt: Path) -> list[Path]:
    """Todos os arquivos da exportação exceto o chat e arquivos ocultos."""
    return sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p != chat_txt and not p.name.startswith(".")
    )
