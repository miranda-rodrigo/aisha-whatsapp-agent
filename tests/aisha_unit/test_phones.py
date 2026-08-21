import unittest

from aisha.phones import (
    is_allowed_number,
    normalize_phone,
    parse_allowed_numbers,
    phone_match_keys,
)


class PhoneAllowlistTests(unittest.TestCase):
    def test_normalize_strips_plus_spaces_and_punctuation(self):
        self.assertEqual(normalize_phone("+55 85 99065-040"), "558599065040")
        self.assertEqual(normalize_phone(" 558599065040 "), "558599065040")

    def test_parse_trims_spaces_around_commas(self):
        allowed = parse_allowed_numbers("558599065040, 558591355300")
        self.assertIn("558599065040", allowed)
        self.assertIn("558591355300", allowed)

    def test_parse_ignores_empty_and_plus(self):
        allowed = parse_allowed_numbers("+558599065040, ,558591355300")
        self.assertTrue(is_allowed_number("558599065040", allowed))
        self.assertTrue(is_allowed_number("558591355300", allowed))

    def test_br_extra_nine_matches_in_both_directions(self):
        allowed_short = parse_allowed_numbers("558599065040")
        self.assertTrue(is_allowed_number("5585999065040", allowed_short))
        self.assertTrue(is_allowed_number("558599065040", allowed_short))

        allowed_long = parse_allowed_numbers("5585999065040")
        self.assertTrue(is_allowed_number("558599065040", allowed_long))
        self.assertTrue(is_allowed_number("+55 85 9 9906-5040", allowed_long))

    def test_rejects_unrelated_number(self):
        allowed = parse_allowed_numbers("558599065040,558591355300")
        self.assertFalse(is_allowed_number("5511888888888", allowed))
        self.assertFalse(is_allowed_number("", allowed))
        self.assertFalse(is_allowed_number("558599065040", set()))

    def test_patched_allowlist_without_aliases_still_matches_sender(self):
        # Webhook tests patch ALLOWED_NUMBERS with the raw set.
        self.assertTrue(is_allowed_number("5511999999999", {"5511999999999"}))
        self.assertTrue(is_allowed_number("5585999065040", {"558599065040"}))

    def test_phone_match_keys_cover_meta_and_local_forms(self):
        keys = phone_match_keys("558599065040")
        self.assertEqual(keys, {"558599065040", "5585999065040"})


if __name__ == "__main__":
    unittest.main()
