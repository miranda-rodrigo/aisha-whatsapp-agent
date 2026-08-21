"""Mapa estático com círculo geodésico em torno de um endereço ou ponto.

Geocodifica via Nominatim e desenha o raio sobre tiles OpenStreetMap.
O PNG fica num store em memória por telefone — não vai no contexto do modelo.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import unicodedata
from typing import Any

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "Aisha/1.0 (contato@askaisha.com.br)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

MIN_RADIUS_M = 50
MAX_RADIUS_M = 50_000
IMAGE_SIZE = 800
TILE_SIZE = 256
CIRCLE_POINTS = 64
CIRCLE_FIT = 0.70
CLUSTER_M = 200
MAX_CANDIDATES = 5
MIN_ZOOM = 3
MAX_ZOOM = 18
EARTH_RADIUS_M = 6_371_000.0
EARTH_CIRCUMFERENCE_M = 40_075_016.686
MERCATOR_MAX_LAT = 85.05112878

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


def store_map_image(phone: str, png: bytes) -> None:
    _last_maps[phone] = png


def pop_map_image(phone: str) -> bytes | None:
    return _last_maps.pop(phone, None)


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _parse_number(raw: str) -> float:
    text = raw.strip().replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    return float(text)


_RADIUS_UNIT_RE = (
    r"km|quilometros?|kilometros?|kilometers?|"
    r"metros?|meters?|mi|milhas?|miles?|m"
)


def extract_radius_from_text(text: str) -> tuple[str, str | None] | None:
    """Extrai (valor, unidade) de uma frase. None se não houver raio."""
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None
    try:
        parse_radius_meters(raw)
        return raw, None
    except ValueError:
        pass
    folded = _strip_accents(raw)
    match = re.search(
        rf"([\d.,]+)\s*({_RADIUS_UNIT_RE})\b",
        folded,
        re.IGNORECASE,
    )
    if match:
        return match.group(1), match.group(2)
    match = re.search(r"\braio\b[^\d]{0,24}([\d.,]+)\b", folded, re.IGNORECASE)
    if match:
        return match.group(1), None
    return None


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


def format_map_caption(payload: dict) -> str:
    """Texto curto para acompanhar o PNG do mapa no WhatsApp."""
    name = (payload.get("display_name") or "").strip()
    radius_label = payload.get("radius_label") or ""
    area_label = payload.get("area_label") or ""
    lat = payload.get("lat")
    lng = payload.get("lng")
    maps_url = payload.get("maps_url") or ""
    lines: list[str] = []
    if name:
        lines.append(f"📍 {name}")
    if radius_label:
        extra = f" (área {area_label})" if area_label else ""
        lines.append(f"Raio: {radius_label}{extra}")
    if lat is not None and lng is not None:
        lines.append(f"Coordenadas: {lat}, {lng}")
    if maps_url:
        lines.append(maps_url)
    if payload.get("unit_assumed") == "km":
        lines.append("Interpretei o raio em quilômetros.")
    return "\n".join(lines)


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


def latlng_to_world_pixels(lat: float, lng: float, zoom: int) -> tuple[float, float]:
    n = TILE_SIZE * (2 ** zoom)
    x = (lng + 180.0) / 360.0 * n
    lat_c = max(min(lat, MERCATOR_MAX_LAT), -MERCATOR_MAX_LAT)
    sin_lat = math.sin(math.radians(lat_c))
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * n
    return x, y


def choose_zoom(lat: float, radius_m: float) -> int:
    target_mpp = (2 * radius_m) / (CIRCLE_FIT * IMAGE_SIZE)
    cos_lat = max(math.cos(math.radians(lat)), 0.01)
    zoom_f = math.log2(cos_lat * EARTH_CIRCUMFERENCE_M / (TILE_SIZE * target_mpp))
    return max(MIN_ZOOM, min(MAX_ZOOM, int(round(zoom_f))))


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


async def reverse_geocode(lat: float, lng: float, client: httpx.AsyncClient) -> str | None:
    try:
        resp = await client.get(
            NOMINATIM_REVERSE_URL,
            params={"lat": lat, "lon": lng, "format": "json"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("Reverse geocode failed for %s,%s", lat, lng)
        return None
    name = (data.get("display_name") or "").strip()
    return name or None


async def _fetch_tile(client: httpx.AsyncClient, z: int, x: int, y: int) -> tuple[tuple[int, int], bytes]:
    resp = await client.get(TILE_URL.format(z=z, x=x, y=y))
    resp.raise_for_status()
    return (x, y), resp.content


async def _fetch_tiles(
    client: httpx.AsyncClient,
    zoom: int,
    coords: list[tuple[int, int]],
) -> dict[tuple[int, int], bytes]:
    sem = asyncio.Semaphore(8)

    async def one(x: int, y: int):
        async with sem:
            return await _fetch_tile(client, zoom, x, y)

    pairs = await asyncio.gather(*[one(x, y) for x, y in coords])
    return dict(pairs)


def _tile_window(lat: float, lng: float, radius_m: float, zoom: int) -> tuple[int, int, int, int]:
    pad_m = radius_m / CIRCLE_FIT
    north, _ = destination_point(lat, lng, pad_m, 0.0)
    south, _ = destination_point(lat, lng, pad_m, math.pi)
    _, east = destination_point(lat, lng, pad_m, math.pi / 2)
    _, west = destination_point(lat, lng, pad_m, 3 * math.pi / 2)
    n_tiles = 2 ** zoom
    corners = [
        latlng_to_world_pixels(north, west, zoom),
        latlng_to_world_pixels(north, east, zoom),
        latlng_to_world_pixels(south, west, zoom),
        latlng_to_world_pixels(south, east, zoom),
        latlng_to_world_pixels(lat, lng, zoom),
    ]
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    x_min = max(0, int(math.floor(min(xs) / TILE_SIZE)))
    y_min = max(0, int(math.floor(min(ys) / TILE_SIZE)))
    x_max = min(n_tiles - 1, int(math.floor(max(xs) / TILE_SIZE)))
    y_max = min(n_tiles - 1, int(math.floor(max(ys) / TILE_SIZE)))
    return x_min, y_min, x_max, y_max


def _render_map_png(
    tiles: dict[tuple[int, int], bytes],
    zoom: int,
    x_min: int,
    y_min: int,
    x_max: int,
    y_max: int,
    lat: float,
    lng: float,
    radius_m: float,
) -> bytes:
    import pymupdf

    mosaic_w = (x_max - x_min + 1) * TILE_SIZE
    mosaic_h = (y_max - y_min + 1) * TILE_SIZE
    origin_x = x_min * TILE_SIZE
    origin_y = y_min * TILE_SIZE

    doc = pymupdf.open()
    page = doc.new_page(width=mosaic_w, height=mosaic_h)
    for tx in range(x_min, x_max + 1):
        for ty in range(y_min, y_max + 1):
            png = tiles.get((tx, ty))
            if not png:
                continue
            px = (tx - x_min) * TILE_SIZE
            py = (ty - y_min) * TILE_SIZE
            page.insert_image(pymupdf.Rect(px, py, px + TILE_SIZE, py + TILE_SIZE), stream=png)

    points = []
    for clat, clng in geodesic_circle(lat, lng, radius_m):
        wx, wy = latlng_to_world_pixels(clat, clng, zoom)
        points.append(pymupdf.Point(wx - origin_x, wy - origin_y))
    if points:
        points.append(points[0])
        shape = page.new_shape()
        shape.draw_polyline(points)
        shape.finish(
            color=(0.12, 0.40, 0.75),
            fill=(0.12, 0.53, 0.90),
            width=3,
            closePath=True,
            fill_opacity=0.28,
        )
        shape.commit()

    cx, cy = latlng_to_world_pixels(lat, lng, zoom)
    rel_cx, rel_cy = cx - origin_x, cy - origin_y
    page.draw_circle(
        pymupdf.Point(rel_cx, rel_cy),
        7,
        color=(0.85, 0.15, 0.15),
        fill=(0.85, 0.15, 0.15),
        width=1,
    )
    page.draw_circle(
        pymupdf.Point(rel_cx, rel_cy),
        11,
        color=(0.85, 0.15, 0.15),
        fill=None,
        width=2,
    )

    clip_x0 = rel_cx - IMAGE_SIZE / 2
    clip_y0 = rel_cy - IMAGE_SIZE / 2
    clip_x0 = min(max(clip_x0, 0), max(0, mosaic_w - IMAGE_SIZE))
    clip_y0 = min(max(clip_y0, 0), max(0, mosaic_h - IMAGE_SIZE))
    clip_w = min(IMAGE_SIZE, mosaic_w)
    clip_h = min(IMAGE_SIZE, mosaic_h)
    clip = pymupdf.Rect(clip_x0, clip_y0, clip_x0 + clip_w, clip_y0 + clip_h)
    pix = page.get_pixmap(clip=clip, alpha=False)
    png = pix.tobytes("png")
    doc.close()
    return png


async def render_osm_map(
    client: httpx.AsyncClient,
    lat: float,
    lng: float,
    radius_m: float,
) -> bytes:
    zoom = choose_zoom(lat, radius_m)
    x_min, y_min, x_max, y_max = _tile_window(lat, lng, radius_m, zoom)
    coords = [(x, y) for x in range(x_min, x_max + 1) for y in range(y_min, y_max + 1)]
    while len(coords) > 25 and zoom > MIN_ZOOM:
        zoom -= 1
        x_min, y_min, x_max, y_max = _tile_window(lat, lng, radius_m, zoom)
        coords = [(x, y) for x in range(x_min, x_max + 1) for y in range(y_min, y_max + 1)]
    tiles = await _fetch_tiles(client, zoom, coords[:25])
    return _render_map_png(tiles, zoom, x_min, y_min, x_max, y_max, lat, lng, radius_m)


async def render_radius_map(
    client: httpx.AsyncClient,
    lat: float,
    lng: float,
    radius_m: float,
) -> bytes:
    return await render_osm_map(client, lat, lng, radius_m)


def maps_url(lat: float, lng: float, zoom: int | None = None) -> str:
    z = zoom if zoom is not None else 15
    return (
        f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lng:.6f}"
        f"#map={z}/{lat:.5f}/{lng:.5f}"
    )


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
    """Geocodifica (se preciso), pede o PNG e guarda para o telefone."""
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
            elif not display_name:
                display_name = await reverse_geocode(lat, lng, client) or f"{lat:.5f}, {lng:.5f}"
            png = await render_radius_map(client, lat, lng, radius_m)
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
        "maps_url": maps_url(lat, lng, choose_zoom(lat, radius_m)),
    }
    if assumed_km:
        payload["unit_assumed"] = "km"
    return payload
