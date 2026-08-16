import unittest

from aisha.routing import (
    contains_aisha,
    is_download_intent,
    is_retroactive_transcription_request,
    is_transcription_request,
    is_trivial_message,
    parse_page_selection,
    strip_aisha,
    wants_new_session,
)


class RoutingTests(unittest.TestCase):
    def test_contains_aisha(self):
        self.assertTrue(contains_aisha("Aisha, qual o dólar?"))
        self.assertTrue(contains_aisha("oi aisha"))
        self.assertFalse(contains_aisha("transcreve isso"))

    def test_strip_aisha(self):
        self.assertEqual(strip_aisha("Aisha, resume isso"), "resume isso")

    def test_download_intent(self):
        self.assertTrue(is_download_intent("baixa esse vídeo"))
        self.assertTrue(is_download_intent("me manda o download"))
        self.assertFalse(is_download_intent("resume o vídeo"))

    def test_retroactive_transcription(self):
        self.assertTrue(is_retroactive_transcription_request("eu só queria a transcrição"))
        self.assertFalse(is_retroactive_transcription_request("qual o dólar hoje?"))

    def test_explicit_transcription(self):
        self.assertTrue(is_transcription_request("Aisha, transcreva isso por favor"))
        self.assertFalse(is_transcription_request("Aisha, qual o clima?"))

    def test_new_session(self):
        self.assertTrue(wants_new_session("nova conversa"))
        self.assertTrue(wants_new_session("reset"))
        self.assertFalse(wants_new_session("me lembra amanhã"))

    def test_trivial_message(self):
        self.assertTrue(is_trivial_message("oi"))
        self.assertTrue(is_trivial_message("obrigado!"))
        self.assertTrue(is_trivial_message("bom dia"))
        self.assertFalse(is_trivial_message("oi, me lembra da reunião"))
        self.assertFalse(is_trivial_message("qual o dólar hoje?"))

    def test_parse_page_selection_range(self):
        self.assertEqual(parse_page_selection("páginas 1 a 5", 20), [0, 1, 2, 3, 4])

    def test_parse_page_selection_list(self):
        self.assertEqual(parse_page_selection("páginas 2, 4 e 7", 10), [1, 3, 6])

    def test_parse_page_selection_single(self):
        self.assertEqual(parse_page_selection("página 3", 10), [2])

    def test_parse_page_selection_empty(self):
        self.assertIsNone(parse_page_selection("resume o documento", 10))

    def test_parse_page_selection_caps_limit(self):
        pages = parse_page_selection("páginas 1 a 20", 20)
        self.assertEqual(len(pages), 5)


if __name__ == "__main__":
    unittest.main()
