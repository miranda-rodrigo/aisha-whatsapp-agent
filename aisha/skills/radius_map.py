"""Mapa estático com círculo geodésico em torno de um endereço ou ponto.

Geocodifica via Nominatim e pede a imagem à Google Maps Static API
(visual CalcMaps: roadmap, círculo azul, pino vermelho). O PNG fica num
store em memória por telefone — não vai no contexto do modelo.
"""

from __future__ import annotations

import logging
import math
import os
import re
import unicodedata
from typing import Any

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "Aisha/1.0 (contato@askaisha.com.br)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
STATICMAP_URL = "https://maps.googleapis.com/maps/api/staticmap"

MIN_RADIUS_M = 50
MAX_RADIUS_M = 50_000
CIRCLE_POINTS = 64
CLUSTER_M = 200
MAX_CANDIDATES = 5
EARTH_RADIUS_M = 6_371_000.0

# CalcMaps-like overlay: blue fill ~33% opacity, darker blue stroke.
PATH_FILL = "0x1E88E655"
PATH_STROKE = "0x1565C0FF"
PATH_WEIGHT = "2"

_UNIT_TO_METERS = {
    "m": 1.0,
    "metro": 1.0,
    "metros": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "km": 1000.0,
    "quilometro": 1000.0,
    "quilometros": 1000.0,
    "kilometro": 1000.0,
    "kilometros": 1000.0,
    "kilometer": 1000.0,
    "kilometers": 1000.0,
    "mi": 1609.344,
    "milha": 1609.344,
    "milhas": 1609.344,
    "mile": 1609.344,
    "miles": 1609.344,
}

_last_maps: dict[str, bytes] = {}


class MissingMapsApiKey(RuntimeError):
    """GOOGLE_MAPS_API_KEY ausente — sem fallback OSM."""


def store_map_image(phone: str, png: bytes) -> None:
    _last_maps[phone] = png


def pop_map_image(phone: str) -> bytes | None:
    return _last_maps.pop(phone, None)


def maps_api_key() -> str:
    return os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _parse_number(raw: str) -> float:
    text = raw.strip().replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    return float(text)


def parse_radius_meters(value: Any, unit: str | None = None) -> float:
    """Converte raio para metros. Sem unidade, assume km."""
    if value is None or value == "":
        raise ValueError("Informe um raio.")
    unit_key = _strip_accents((unit or "").strip().lower())
    if isinstance(value, str):
        match = re.fullmatch(
            r"\s*([\d.,]+)\s*([a-zA-ZáéíóúãõâêôçÁÉÍÓÚÃÕÂÊÔÇ]*)\s*",
            value,
        )
        if not match:
            raise ValueError("Não entendi o raio. Exemplos: 2 km, 500 m, 1 mi.")
        number = _parse_number(match.group(1))
        from_text = _strip_accents(match.group(2).lower())
        if from_text:
            unit_key = from_text
    else:
        number = float(value)
    factor = _UNIT_TO_METERS.get(unit_key, 1000.0 if not unit_key else None)
    if factor is None:
        raise ValueError("Unidade de raio inválida. Use m, km ou mi.")
    return number * factor


def validate_radius_m(radius_m: float) -> float:
    if radius_m < MIN_RADIUS_M or radius_m > MAX_RADIUS_M:
        raise ValueError("O raio precisa estar entre 50 m e 50 km.")
    return radius_m


def format_radius(radius_m: float) -> str:
    if radius_m >= 1000:
        km = radius_m / 1000.0
        if abs(km - round(km)) < 1e-9:
            return f"{int(round(km))} km"
        text = f"{km:.1f}".replace(".", ",")
        return f"{text} km"
    if abs(radius_m - round(radius_m)) < 1e-9:
        return f"{int(round(radius_m))} m"
    return f"{radius_m:.0f} m"


def format_area(radius_m: float) -> str:
    area_m2 = math.pi * radius_m * radius_m
    if area_m2 >= 1_000_000:
        km2 = area_m2 / 1_000_000
        return f"{km2:.2f} km²".replace(".", ",")
    return f"{int(round(area_m2))} m²"


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def destination_point(lat: float, lng: float, distance_m: float, bearing_rad: float) -> tuple[float, float]:
    d = distance_m / EARTH_RADIUS_M
    lat1 = math.radians(lat)
    lng1 = math.radians(lng)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(d)
        + math.cos(lat1) * math.sin(d) * math.cos(bearing_rad)
    )
    lng2 = lng1 + math.atan2(
        math.sin(bearing_rad) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), (math.degrees(lng2) + 540) % 360 - 180


def geodesic_circle(lat: float, lng: float, radius_m: float, n: int = CIRCLE_POINTS) -> list[tuple[float, float]]:
    return [destination_point(lat, lng, radius_m, 2 * math.pi * i / n) for i in range(n)]


def encode_polyline(points: list[tuple[float, float]]) -> str:
    """Encoded polyline algorithm da Google Maps Static API."""

    def encode_signed(value: int) -> str:
        value = ~(value << 1) if value < 0 else (value << 1)
        chunks: list[str] = []
        while value >= 0x20:
            chunks.append(chr((0x20 | (value & 0x1F)) + 63))
            value >>= 5
        chunks.append(chr(value + 63))
        return "".join(chunks)

    parts: list[str] = []
    prev_lat = 0
    prev_lng = 0
    for lat, lng in points:
        lat_e5 = int(round(lat * 1e5))
        lng_e5 = int(round(lng * 1e5))
        parts.append(encode_signed(lat_e5 - prev_lat))
        parts.append(encode_signed(lng_e5 - prev_lng))
        prev_lat, prev_lng = lat_e5, lng_e5
    return "".join(parts)


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decodifica para testes: o círculo precisa fechar e ter o raio certo."""
    points: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)
    while index < length:
        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        lat += ~(result >> 1) if result & 1 else (result >> 1)
        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        lng += ~(result >> 1) if result & 1 else (result >> 1)
        points.append((lat / 1e5, lng / 1e5))
    return points


def closed_circle_path(lat: float, lng: float, radius_m: float) -> str:
    pts = geodesic_circle(lat, lng, radius_m)
    pts.append(pts[0])
    return (
        f"fillcolor:{PATH_FILL}|color:{PATH_STROKE}|weight:{PATH_WEIGHT}"
        f"|enc:{encode_polyline(pts)}"
    )


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _candidate(row: dict, index: int) -> dict:
    return {
        "index": index,
        "display_name": row.get("display_name") or "",
        "lat": float(row["lat"]),
        "lng": float(row["lon"]),
    }


def _clustered_unique(results: list[dict]) -> bool:
    first = results[0]
    lat0, lng0 = float(first["lat"]), float(first["lon"])
    return all(
        haversine_m(lat0, lng0, float(row["lat"]), float(row["lon"])) <= CLUSTER_M
        for row in results
    )


async def geocode_address(address: str, client: httpx.AsyncClient) -> dict:
    resp = await client.get(
        NOMINATIM_URL,
        params={"q": address, "format": "json", "limit": str(MAX_CANDIDATES)},
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return {
            "error": "Não encontrei esse endereço. Envie um endereço mais específico (rua, número, cidade).",
        }
    if len(results) > 1 and not _clustered_unique(results):
        return {
            "status": "ambiguous",
            "candidates": [_candidate(row, i) for i, row in enumerate(results[:MAX_CANDIDATES], 1)],
        }
    chosen = _candidate(results[0], 1)
    chosen["status"] = "ok"
    return chosen


def static_map_params(lat: float, lng: float, radius_m: float, api_key: str) -> dict[str, str]:
    return {
        "size": "640x640",
        "scale": "2",
        "maptype": "roadmap",
        "language": "pt-BR",
        "region": "BR",
        "markers": f"color:red|{lat:.6f},{lng:.6f}",
        "path": closed_circle_path(lat, lng, radius_m),
        "key": api_key,
    }


async def render_radius_map(
    client: httpx.AsyncClient,
    lat: float,
    lng: float,
    radius_m: float,
) -> bytes:
    key = maps_api_key()
    if not key:
        raise MissingMapsApiKey(
            "Mapa com raio precisa da chave GOOGLE_MAPS_API_KEY "
            "(Google Maps Static API). Sem ela não consigo gerar o mapa."
        )
    resp = await client.get(STATICMAP_URL, params=static_map_params(lat, lng, radius_m, key))
    resp.raise_for_status()
    content = resp.content or b""
    stripped = content.lstrip()
    if stripped.startswith(b"<") or stripped.startswith(b"{"):
        raise RuntimeError(f"Google Static Maps recusou o pedido: {content[:200]!r}")
    if not (content.startswith(b"\x89PNG") or content.startswith(b"GIF") or content.startswith(b"\xff\xd8")):
        raise RuntimeError("Google Static Maps não devolveu uma imagem.")
    return content


def maps_url(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps?q={lat:.6f},{lng:.6f}"


def unit_was_assumed(value: Any, unit: str | None) -> bool:
    if unit and str(unit).strip():
        return False
    if isinstance(value, str) and re.search(r"[A-Za-zÁÉÍÓÚáéíóúÃÕÂÊÔÇãõâêôç]", value):
        return False
    return True


async def build_radius_map(
    phone: str,
    address: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius: Any = None,
    unit: str | None = None,
) -> dict:
    """Geocodifica (se preciso), pede o PNG ao Google e guarda para o telefone."""
    try:
        radius_m = validate_radius_m(parse_radius_meters(radius, unit))
    except ValueError as exc:
        return {"error": str(exc)}

    lat = _as_float(latitude)
    lng = _as_float(longitude)
    display_name = (address or "").strip()
    assumed_km = unit_was_assumed(radius, unit)

    headers = {"User-Agent": USER_AGENT}
    timeout = httpx.Timeout(20.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
            if lat is None or lng is None:
                if not display_name:
                    return {"error": "Informe um endereço (ou coordenadas) e um raio."}
                geo = await geocode_address(display_name, client)
                if geo.get("error") or geo.get("status") == "ambiguous":
                    return geo
                lat = geo["lat"]
                lng = geo["lng"]
                display_name = geo["display_name"] or display_name
            png = await render_radius_map(client, lat, lng, radius_m)
    except MissingMapsApiKey as exc:
        return {"error": str(exc)}
    except Exception:
        log.exception("Failed to build radius map")
        return {"error": "Não consegui montar o mapa agora. Tente de novo em instantes."}

    store_map_image(phone, png)
    log.info(
        "Radius map ready: phone=%s lat=%.5f lng=%.5f r=%.0fm bytes=%s",
        phone, lat, lng, radius_m, len(png),
    )
    payload = {
        "status": "ok",
        "display_name": display_name or f"{lat:.5f}, {lng:.5f}",
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "radius_m": int(round(radius_m)),
        "radius_label": format_radius(radius_m),
        "area_label": format_area(radius_m),
        "maps_url": maps_url(lat, lng),
    }
    if assumed_km:
        payload["unit_assumed"] = "km"
    return payload
