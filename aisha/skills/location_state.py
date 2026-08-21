"""Store for WhatsApp location pins awaiting a radius (memory + Supabase)."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from aisha.skills.pending_store import clear_pending, upsert_pending

LOCATION_PENDING_TTL = 600  # 10 minutes — same as the chat session window


@dataclass
class PendingLocation:
    lat: float
    lng: float
    name: str = ""
    address: str = ""
    url: str = ""
    timestamp: float = 0.0

    @property
    def label(self) -> str:
        if self.name and self.address:
            return f"{self.name}, {self.address}"
        return self.name or self.address or f"{self.lat:.5f}, {self.lng:.5f}"

    def to_payload(self) -> dict:
        return {
            "lat": self.lat,
            "lng": self.lng,
            "name": self.name,
            "address": self.address,
            "url": self.url,
        }


_pending: dict[str, PendingLocation] = {}


def _schedule(coro) -> None:
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        pass


def parse_whatsapp_location(message: dict) -> PendingLocation | None:
    loc = message.get("location")
    if not isinstance(loc, dict):
        return None
    try:
        lat = float(loc["latitude"])
        lng = float(loc["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return None
    return PendingLocation(
        lat=lat,
        lng=lng,
        name=str(loc.get("name") or "").strip(),
        address=str(loc.get("address") or "").strip(),
        url=str(loc.get("url") or "").strip(),
        timestamp=time.monotonic(),
    )


def store_pending_location(
    phone: str,
    lat: float,
    lng: float,
    name: str = "",
    address: str = "",
    url: str = "",
    persist: bool = True,
) -> PendingLocation:
    entry = PendingLocation(
        lat=float(lat),
        lng=float(lng),
        name=(name or "").strip(),
        address=(address or "").strip(),
        url=(url or "").strip(),
        timestamp=time.monotonic(),
    )
    _pending[phone] = entry
    if persist:
        _schedule(upsert_pending(phone, "location", entry.to_payload(), LOCATION_PENDING_TTL))
    return entry


def restore_pending_location(phone: str, payload: dict[str, Any]) -> PendingLocation | None:
    try:
        lat = float(payload["lat"])
        lng = float(payload["lng"])
    except (KeyError, TypeError, ValueError):
        return None
    return store_pending_location(
        phone,
        lat=lat,
        lng=lng,
        name=str(payload.get("name") or ""),
        address=str(payload.get("address") or ""),
        url=str(payload.get("url") or ""),
        persist=False,
    )


def get_pending_location(phone: str) -> PendingLocation | None:
    entry = _pending.get(phone)
    if entry is None:
        return None
    if time.monotonic() - entry.timestamp > LOCATION_PENDING_TTL:
        _pending.pop(phone, None)
        _schedule(clear_pending(phone, "location"))
        return None
    return entry


def clear_pending_location(phone: str) -> None:
    _pending.pop(phone, None)
    _schedule(clear_pending(phone, "location"))


def format_location_received_prompt(loc: PendingLocation) -> str:
    return (
        f"📍 Recebi sua localização: *{loc.label}*\n\n"
        "Qual raio você quer em torno deste ponto? Ex: *500 m* ou *2 km*."
    )


def format_location_for_agent(loc: PendingLocation) -> str:
    lines = [
        "O usuário compartilhou uma localização do WhatsApp.",
        f"latitude: {loc.lat:.6f}",
        f"longitude: {loc.lng:.6f}",
    ]
    if loc.name:
        lines.append(f"nome: {loc.name}")
    if loc.address:
        lines.append(f"endereço: {loc.address}")
    lines.append(
        "Use latitude e longitude como o ponto do mapa. "
        "Se o raio já foi informado nesta conversa, chame draw_radius_map agora. "
        "Se faltar o raio, pergunte só o raio (ex: 500 m, 2 km). "
        "Não peça o endereço de novo."
    )
    return "\n".join(lines)
