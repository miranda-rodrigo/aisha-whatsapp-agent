import unittest
from unittest.mock import patch

from tests.aisha_unit._helpers import configure_test_env

configure_test_env()

from aisha.skills import location_state


class LocationStateTests(unittest.TestCase):
    @staticmethod
    def _close(coro):
        coro.close()

    def setUp(self):
        location_state._pending.clear()

    def tearDown(self):
        location_state._pending.clear()

    def test_parse_whatsapp_location_with_name_and_address(self):
        loc = location_state.parse_whatsapp_location(
            {
                "type": "location",
                "location": {
                    "latitude": "-3.7319",
                    "longitude": "-38.5267",
                    "name": "Assahi Motel",
                    "address": "Avenida Luciano Carneiro, 605, Fortaleza",
                    "url": "https://www.assahimotel.com.br",
                },
            }
        )
        self.assertIsNotNone(loc)
        self.assertAlmostEqual(loc.lat, -3.7319)
        self.assertAlmostEqual(loc.lng, -38.5267)
        self.assertEqual(loc.name, "Assahi Motel")
        self.assertIn("Assahi Motel", loc.label)
        self.assertIn("Avenida Luciano Carneiro", loc.label)

    def test_parse_rejects_missing_or_out_of_range(self):
        self.assertIsNone(location_state.parse_whatsapp_location({"type": "location"}))
        self.assertIsNone(
            location_state.parse_whatsapp_location(
                {"location": {"latitude": 91, "longitude": 0}}
            )
        )
        self.assertIsNone(
            location_state.parse_whatsapp_location(
                {"location": {"latitude": "x", "longitude": "y"}}
            )
        )

    def test_store_get_expire_and_clear(self):
        with patch.object(location_state, "_schedule", side_effect=self._close) as schedule:
            stored = location_state.store_pending_location(
                "5511", lat=-3.73, lng=-38.52, name="Praça"
            )
            entry = location_state.get_pending_location("5511")
            location_state.clear_pending_location("5511")

        self.assertEqual(stored.lat, -3.73)
        self.assertEqual(entry.name, "Praça")
        self.assertIsNone(location_state.get_pending_location("5511"))
        self.assertEqual(schedule.call_count, 2)

    def test_expired_location_is_removed(self):
        location_state._pending["5511"] = location_state.PendingLocation(
            lat=-3.73,
            lng=-38.52,
            timestamp=10,
        )
        with patch.object(
            location_state.time,
            "monotonic",
            return_value=10 + location_state.LOCATION_PENDING_TTL + 1,
        ), patch.object(location_state, "_schedule", side_effect=self._close) as schedule:
            self.assertIsNone(location_state.get_pending_location("5511"))

        schedule.assert_called_once()

    def test_restore_from_payload_does_not_persist(self):
        with patch.object(location_state, "_schedule") as schedule:
            entry = location_state.restore_pending_location(
                "5511",
                {"lat": -3.73, "lng": -38.52, "name": "Centro"},
            )
        self.assertEqual(entry.name, "Centro")
        self.assertEqual(location_state.get_pending_location("5511").lng, -38.52)
        schedule.assert_not_called()

    def test_restore_rejects_bad_payload(self):
        self.assertIsNone(location_state.restore_pending_location("5511", {"lat": "x"}))

    def test_prompts_mention_radius_and_coordinates(self):
        loc = location_state.PendingLocation(
            lat=-3.7319,
            lng=-38.5267,
            name="Assahi Motel",
            address="Av. Luciano Carneiro, 605",
        )
        received = location_state.format_location_received_prompt(loc)
        agent = location_state.format_location_for_agent(loc)
        self.assertIn("Qual raio", received)
        self.assertIn("Assahi Motel", received)
        self.assertIn("latitude: -3.731900", agent)
        self.assertIn("draw_radius_map", agent)
        self.assertIn("Não peça o endereço", agent)


if __name__ == "__main__":
    unittest.main()
