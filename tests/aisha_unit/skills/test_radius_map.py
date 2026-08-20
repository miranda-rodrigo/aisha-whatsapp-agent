"""Testes da skill de mapa com raio — sem rede."""

import struct
import unittest
import zlib
from unittest.mock import AsyncMock, MagicMock, patch

from tests.aisha_unit._helpers import async_http_client, http_response

from aisha.skills import radius_map

FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"fake-map-bytes"


def rgb_png(width: int = 256, height: int = 256, color=(180, 190, 180)) -> bytes:
    pixel = bytes(color)
    row = b"\x00" + pixel * width
    raw = row * height

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


class ParseRadiusTests(unittest.TestCase):
    def test_text_units(self):
        self.assertEqual(radius_map.parse_radius_meters("2 km"), 2000)
        self.assertEqual(radius_map.parse_radius_meters("500 metros"), 500)
        self.assertAlmostEqual(radius_map.parse_radius_meters("1 mi"), 1609.344)
        self.assertEqual(radius_map.parse_radius_meters("2,5 km"), 2500)

    def test_number_without_unit_assumes_km(self):
        self.assertEqual(radius_map.parse_radius_meters(2), 2000)
        self.assertEqual(radius_map.parse_radius_meters("3"), 3000)
        self.assertTrue(radius_map.unit_was_assumed(2, None))
        self.assertFalse(radius_map.unit_was_assumed("500 m", None))
        self.assertFalse(radius_map.unit_was_assumed(2, "km"))

    def test_explicit_unit(self):
        self.assertEqual(radius_map.parse_radius_meters(500, "m"), 500)
        self.assertEqual(radius_map.parse_radius_meters(2, "km"), 2000)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            radius_map.parse_radius_meters(None)
        with self.assertRaises(ValueError):
            radius_map.parse_radius_meters("abc")
        with self.assertRaises(ValueError):
            radius_map.parse_radius_meters(2, "parsecs")
        with self.assertRaises(ValueError):
            radius_map.validate_radius_m(10)
        with self.assertRaises(ValueError):
            radius_map.validate_radius_m(100_000)

    def test_format_radius_and_area(self):
        self.assertEqual(radius_map.format_radius(2000), "2 km")
        self.assertEqual(radius_map.format_radius(500), "500 m")
        self.assertEqual(radius_map.format_radius(2500), "2,5 km")
        self.assertEqual(radius_map.format_area(5000), "78,54 km²")
        self.assertEqual(radius_map.format_area(500), "785398 m²")


class GeometryTests(unittest.TestCase):
    def test_geodesic_circle_north_point(self):
        lat, lng = -3.7319, -38.5267
        north_lat, north_lng = radius_map.destination_point(lat, lng, 2000, 0.0)
        self.assertGreater(north_lat, lat)
        self.assertAlmostEqual(north_lng, lng, places=3)
        dist = radius_map.haversine_m(lat, lng, north_lat, north_lng)
        self.assertAlmostEqual(dist, 2000, delta=5)

    def test_circle_has_expected_count_and_closes(self):
        pts = radius_map.geodesic_circle(-3.73, -38.52, 2000)
        self.assertEqual(len(pts), radius_map.CIRCLE_POINTS)
        d0 = radius_map.haversine_m(-3.73, -38.52, *pts[0])
        dhalf = radius_map.haversine_m(-3.73, -38.52, *pts[len(pts) // 2])
        self.assertAlmostEqual(d0, 2000, delta=10)
        self.assertAlmostEqual(dhalf, 2000, delta=10)

    def test_polyline_closes_and_keeps_radius(self):
        lat, lng, radius_m = -3.73, -38.52, 5000.0
        path = radius_map.closed_circle_path(lat, lng, radius_m)
        self.assertIn("enc:", path)
        self.assertIn(f"fillcolor:{radius_map.PATH_FILL}", path)
        encoded = path.split("enc:", 1)[1]
        pts = radius_map.decode_polyline(encoded)
        self.assertEqual(len(pts), radius_map.CIRCLE_POINTS + 1)
        self.assertAlmostEqual(pts[0][0], pts[-1][0], places=4)
        self.assertAlmostEqual(pts[0][1], pts[-1][1], places=4)
        for point in pts[:-1]:
            self.assertAlmostEqual(
                radius_map.haversine_m(lat, lng, *point), radius_m, delta=20
            )

    def test_world_pixels_increase_east_and_south(self):
        x0, y0 = radius_map.latlng_to_world_pixels(-3.73, -38.52, 14)
        xe, ye = radius_map.latlng_to_world_pixels(-3.73, -38.50, 14)
        xs, ys = radius_map.latlng_to_world_pixels(-3.75, -38.52, 14)
        self.assertGreater(xe, x0)
        self.assertGreater(ys, y0)

    def test_zoom_keeps_circle_in_view(self):
        z = radius_map.choose_zoom(-3.73, 2000)
        self.assertGreaterEqual(z, radius_map.MIN_ZOOM)
        self.assertLessEqual(z, radius_map.MAX_ZOOM)
        z_big = radius_map.choose_zoom(-3.73, 50_000)
        self.assertLess(z_big, z)


class GeocodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_zero_results(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=http_response(json_data=[]))
        result = await radius_map.geocode_address("lugar nenhum", client)
        self.assertIn("error", result)

    async def test_single_result(self):
        client = MagicMock()
        client.get = AsyncMock(
            return_value=http_response(
                json_data=[{"display_name": "Fortaleza, CE", "lat": "-3.73", "lon": "-38.52"}]
            )
        )
        result = await radius_map.geocode_address("Fortaleza", client)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["lat"], -3.73)
        self.assertEqual(result["lng"], -38.52)

    async def test_nearby_results_collapse(self):
        client = MagicMock()
        client.get = AsyncMock(
            return_value=http_response(
                json_data=[
                    {"display_name": "Rua A, 100", "lat": "-3.73000", "lon": "-38.52000"},
                    {"display_name": "Rua A, 110", "lat": "-3.73050", "lon": "-38.52000"},
                ]
            )
        )
        result = await radius_map.geocode_address("Rua A", client)
        self.assertEqual(result["status"], "ok")

    async def test_distant_results_are_ambiguous(self):
        client = MagicMock()
        client.get = AsyncMock(
            return_value=http_response(
                json_data=[
                    {"display_name": "Fortaleza, CE", "lat": "-3.73", "lon": "-38.52"},
                    {"display_name": "Fortaleza, MG", "lat": "-20.89", "lon": "-45.00"},
                ]
            )
        )
        result = await radius_map.geocode_address("Fortaleza", client)
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 2)


class BuildMapTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        radius_map._last_maps.clear()

    async def test_missing_inputs(self):
        result = await radius_map.build_radius_map("5511", radius=2, unit="km")
        self.assertIn("endereço", result["error"].lower())
        result = await radius_map.build_radius_map("5511", address="Fortaleza")
        self.assertIn("raio", result["error"].lower())

    async def test_out_of_range_radius(self):
        result = await radius_map.build_radius_map("5511", address="Fortaleza", radius=10, unit="m")
        self.assertIn("50 m", result["error"])

    async def test_stores_png_without_putting_it_in_payload(self):
        factory, client = async_http_client(
            http_response(
                json_data=[{"display_name": "Av. Beira Mar, Fortaleza", "lat": "-3.73", "lon": "-38.52"}]
            )
        )
        with patch.object(radius_map.httpx, "AsyncClient", factory), patch.object(
            radius_map, "render_radius_map", AsyncMock(return_value=(FAKE_PNG, "google"))
        ) as render:
            result = await radius_map.build_radius_map(
                "5511", address="Beira Mar, Fortaleza", radius=2, unit="km"
            )
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("png", result)
        self.assertNotIn("image", result)
        self.assertEqual(result["radius_m"], 2000)
        self.assertEqual(result["radius_label"], "2 km")
        self.assertEqual(result["area_label"], "12,57 km²")
        self.assertIn("google.com/maps", result["maps_url"])
        self.assertEqual(result["source"], "google")
        self.assertEqual(radius_map.pop_map_image("5511"), FAKE_PNG)
        self.assertIsNone(radius_map.pop_map_image("5511"))
        render.assert_awaited_once()
        self.assertEqual(client.get.await_count, 1)

    async def test_coordinates_skip_geocode(self):
        factory, client = async_http_client()
        with patch.object(radius_map.httpx, "AsyncClient", factory), patch.object(
            radius_map, "render_radius_map", AsyncMock(return_value=(FAKE_PNG, "google"))
        ):
            result = await radius_map.build_radius_map(
                "5511", latitude=-3.73, longitude=-38.52, radius=500, unit="m"
            )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["lat"], -3.73)
        client.get.assert_not_called()

    async def test_assumes_km_when_unit_omitted(self):
        factory, _ = async_http_client()
        with patch.object(radius_map.httpx, "AsyncClient", factory), patch.object(
            radius_map, "render_radius_map", AsyncMock(return_value=(FAKE_PNG, "osm"))
        ):
            result = await radius_map.build_radius_map(
                "5511", latitude=-3.73, longitude=-38.52, radius=2
            )
        self.assertEqual(result["radius_m"], 2000)
        self.assertEqual(result["unit_assumed"], "km")
        self.assertEqual(result["source"], "osm")


class StaticMapTests(unittest.IsolatedAsyncioTestCase):
    async def test_requests_google_static_map_without_center_or_zoom(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=http_response(content=FAKE_PNG))
        with patch.object(radius_map, "maps_api_key", return_value="test-key"):
            png, source = await radius_map.render_radius_map(client, -3.73, -38.52, 5000)
        self.assertEqual(png, FAKE_PNG)
        self.assertEqual(source, "google")
        url, kwargs = client.get.await_args.args[0], client.get.await_args.kwargs
        self.assertEqual(url, radius_map.STATICMAP_URL)
        params = kwargs["params"]
        self.assertEqual(params["size"], "640x640")
        self.assertEqual(params["scale"], "2")
        self.assertEqual(params["maptype"], "roadmap")
        self.assertEqual(params["markers"], "color:red|-3.730000,-38.520000")
        self.assertIn("enc:", params["path"])
        self.assertNotIn("center", params)
        self.assertNotIn("zoom", params)
        self.assertEqual(params["key"], "test-key")

    async def test_missing_api_key_falls_back_to_osm(self):
        client = MagicMock()
        with patch.object(radius_map, "maps_api_key", return_value=""):
            with patch.object(
                radius_map, "render_osm_map", AsyncMock(return_value=FAKE_PNG)
            ) as osm:
                png, source = await radius_map.render_radius_map(client, -3.73, -38.52, 2000)
        self.assertEqual(png, FAKE_PNG)
        self.assertEqual(source, "osm")
        osm.assert_awaited_once()
        client.get.assert_not_called()

    async def test_google_failure_falls_back_to_osm(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=http_response(content=b'{"error":"denied"}'))
        with patch.object(radius_map, "maps_api_key", return_value="test-key"):
            with patch.object(
                radius_map, "render_osm_map", AsyncMock(return_value=FAKE_PNG)
            ) as osm:
                png, source = await radius_map.render_radius_map(client, -3.73, -38.52, 5000)
        self.assertEqual(png, FAKE_PNG)
        self.assertEqual(source, "osm")
        osm.assert_awaited_once()


class OsmRenderTests(unittest.TestCase):
    def test_render_png_is_nonempty(self):
        try:
            import pymupdf  # noqa: F401
        except ImportError:
            self.skipTest("pymupdf não instalado neste ambiente")
        tile = rgb_png()
        lat, lng = -3.73, -38.52
        zoom = 14
        cx, cy = radius_map.latlng_to_world_pixels(lat, lng, zoom)
        tx, ty = int(cx // 256), int(cy // 256)
        tiles = {(tx, ty): tile, (tx + 1, ty): tile, (tx, ty + 1): tile, (tx + 1, ty + 1): tile}
        png = radius_map._render_map_png(tiles, zoom, tx, ty, tx + 1, ty + 1, lat, lng, 2000)
        self.assertGreater(len(png), 100)
        self.assertTrue(png.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
