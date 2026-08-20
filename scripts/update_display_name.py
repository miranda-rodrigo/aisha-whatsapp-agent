#!/usr/bin/env python3
"""Solicita a troca do nome de exibição (display name) do número WhatsApp Business.

O nome que aparece para os contatos (ex.: "Rodrigo's claro") não é definido no
código — ele pertence ao número no WhatsApp Manager da Meta. Este script usa a
Graph API para pedir a troca, que passa por revisão da Meta (horas a dias).

Requisitos:
- Env vars WHATSAPP_TOKEN e WHATSAPP_PHONE_ID (as mesmas do app / .env).
- O token precisa da permissão `whatsapp_business_management`.

Uso:
    python scripts/update_display_name.py --name "Aisha"
    python scripts/update_display_name.py --status-only

Se a API recusar (erro de permissão), o caminho manual é o WhatsApp Manager:
Configurações do número -> Nome de exibição.
"""

import argparse
import os
import sys

import httpx
from dotenv import load_dotenv

GRAPH_VERSION = "v22.0"
STATUS_FIELDS = "verified_name,display_phone_number,name_status,new_name_status"


def _print_status(client: httpx.Client, phone_id: str) -> None:
    resp = client.get(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{phone_id}",
        params={"fields": STATUS_FIELDS},
    )
    data = resp.json()
    if resp.status_code != 200:
        print(f"Erro ao consultar o número ({resp.status_code}): {data}", file=sys.stderr)
        sys.exit(1)
    print("Estado atual do número:")
    print(f"  Número:            {data.get('display_phone_number', '?')}")
    print(f"  Nome verificado:   {data.get('verified_name', '?')}")
    print(f"  Status do nome:    {data.get('name_status', '?')}")
    print(f"  Status do novo nome: {data.get('new_name_status', '—')}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Troca o display name do número WhatsApp.")
    parser.add_argument("--name", default="Aisha", help="Novo nome de exibição (default: Aisha)")
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Só consulta o status atual do nome, sem pedir troca",
    )
    args = parser.parse_args()

    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("WHATSAPP_PHONE_ID")
    if not token or not phone_id:
        print("Defina WHATSAPP_TOKEN e WHATSAPP_PHONE_ID no ambiente ou no .env.", file=sys.stderr)
        sys.exit(1)

    with httpx.Client(
        headers={"Authorization": f"Bearer {token}"}, timeout=30.0
    ) as client:
        _print_status(client, phone_id)
        if args.status_only:
            return

        print(f"\nSolicitando troca do display name para: {args.name!r}...")
        resp = client.post(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{phone_id}",
            params={"new_display_name": args.name},
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("success"):
            print("Solicitação enviada. A Meta revisa o nome (pode levar horas ou dias).")
            print("Acompanhe com: python scripts/update_display_name.py --status-only")
        else:
            print(f"A API recusou a solicitação ({resp.status_code}): {data}", file=sys.stderr)
            print(
                "Caminho manual: WhatsApp Manager -> Configurações do número -> Nome de exibição.",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
