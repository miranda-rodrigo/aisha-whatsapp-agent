"""Linha de comando: inventário e dossiê."""

from __future__ import annotations

import argparse
from pathlib import Path

from .dossier import generate_dossier
from .inventory import build_inventory, format_inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wa_dossier",
        description="Transforma exportações de WhatsApp em dossiês analisáveis por IA.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_inv = sub.add_parser("inventory", help="Relatório do que veio na exportação")
    p_inv.add_argument("source", type=Path, help=".zip exportado ou pasta já extraída")

    p_dos = sub.add_parser("dossier", help="Gera conversa.md (v0, sem IA)")
    p_dos.add_argument("source", type=Path)
    p_dos.add_argument("-o", "--output", type=Path, default=Path("output"))

    args = parser.parse_args(argv)

    if args.command == "inventory":
        print(format_inventory(build_inventory(args.source)))
    elif args.command == "dossier":
        out = generate_dossier(args.source, args.output)
        print(f"Dossiê gerado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
