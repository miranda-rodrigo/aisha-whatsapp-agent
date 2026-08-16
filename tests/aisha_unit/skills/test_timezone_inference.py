import unittest

from tests.aisha_unit._helpers import configure_test_env

configure_test_env()

from aisha.skills.timezone_inference import infer_timezone


class TimezoneInferenceTests(unittest.TestCase):
    def test_infers_brazil_ddd_after_normalization(self):
        self.assertEqual(infer_timezone("+55 (68) 99999-0000"), "America/Rio_Branco")

    def test_prefers_three_digit_country_code(self):
        self.assertEqual(infer_timezone("+353 87 123 4567"), "Europe/Dublin")

    def test_returns_none_for_ambiguous_or_unknown_numbers(self):
        for phone in ("+1 212 555 0100", "+55 00 99999-0000", "", "999999"):
            with self.subTest(phone=phone):
                self.assertIsNone(infer_timezone(phone))
