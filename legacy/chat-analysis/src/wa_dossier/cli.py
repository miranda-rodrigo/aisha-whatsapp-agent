"""Linha de comando: inventário e dossiê."""

from __future__ import annotations

import argparse
from pathlib import Path

from .build import build
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

    p_build = sub.add_parser(
        "build",
        help="Gera HTML + Markdown. Níveis: 0 leitura, 1 +transcrições, 2 +comentários, 3 +análise")
    p_build.add_argument("source", type=Path, help=".zip exportado ou pasta já extraída")
    p_build.add_argument("-o", "--output", type=Path, default=Path("output"))
    p_build.add_argument("--nivel", type=int, default=0, choices=(0, 1, 2, 3))
    p_build.add_argument("--objetivo", default="")
    p_build.add_argument("--me", default=None, help="Seu nome no chat; suas mensagens ficam à direita")
    p_build.add_argument("--limit", type=int, default=None,
                         help="Processa só as N primeiras mídias de cada etapa (para testar)")
    p_build.add_argument("--desde", default=None,
                         help="Inclui só mensagens a partir desta data (dd/mm/aa)")

    p_dos = sub.add_parser("dossier", help="Gera conversa.md (v0, sem IA)")
    p_dos.add_argument("source", type=Path)
    p_dos.add_argument("-o", "--output", type=Path, default=Path("output"))

    args = parser.parse_args(argv)

    if args.command == "inventory":
        print(format_inventory(build_inventory(args.source)))
    elif args.command == "build":
        build(args.source, args.output, nivel=args.nivel, objetivo=args.objetivo,
              me=args.me, limit=args.limit, desde=args.desde)
    elif args.command == "dossier":
        out = generate_dossier(args.source, args.output)
        print(f"Dossiê gerado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
