"""Normalização de números WhatsApp (allowlist).

A Meta manda `from` só com dígitos, mas o valor no Railway quase sempre
diverge: espaço depois da vírgula, `+`, ou o 9 extra do celular BR.
"""

from __future__ import annotations


def normalize_phone(raw: str) -> str:
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def phone_match_keys(raw: str) -> set[str]:
    """Formas equivalentes do mesmo número, para comparar sender × allowlist.

    Celular BR: 55 + DDD (2) + 9 + 8 dígitos (13) ou sem o 9 extra (12),
    que é o que a Cloud API costuma enviar.
    """
    digits = normalize_phone(raw)
    if not digits:
        return set()
    keys = {digits}
    if digits.startswith("55") and len(digits) == 13 and digits[4] == "9":
        keys.add(digits[:4] + digits[5:])
    if digits.startswith("55") and len(digits) == 12:
        keys.add(digits[:4] + "9" + digits[4:])
    return keys


def parse_allowed_numbers(raw: str) -> set[str]:
    allowed: set[str] = set()
    for part in (raw or "").split(","):
        allowed.update(phone_match_keys(part))
    return allowed


def is_allowed_number(sender: str, allowed: set[str]) -> bool:
    sender_keys = phone_match_keys(sender)
    if not sender_keys or not allowed:
        return False
    if sender_keys & allowed:
        return True
    allowed_keys: set[str] = set()
    for item in allowed:
        allowed_keys.update(phone_match_keys(item))
    return bool(sender_keys & allowed_keys)
