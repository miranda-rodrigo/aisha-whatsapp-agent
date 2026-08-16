import unittest

from aisha.messaging import WHATSAPP_TEXT_LIMIT, split_whatsapp_text


class SplitWhatsappTextTests(unittest.TestCase):
    def test_short_text_returns_single_chunk(self):
        self.assertEqual(split_whatsapp_text("olá"), ["olá"])

    def test_empty_text_returns_nothing(self):
        self.assertEqual(split_whatsapp_text("   "), [])

    def test_text_at_limit_is_not_split(self):
        text = "a" * WHATSAPP_TEXT_LIMIT
        self.assertEqual(split_whatsapp_text(text), [text])

    def test_long_text_is_split_within_limit(self):
        text = "palavra " * 2000  # ~16k chars
        chunks = split_whatsapp_text(text)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), WHATSAPP_TEXT_LIMIT)
            self.assertTrue(chunk)

    def test_prefers_paragraph_boundary(self):
        para1 = "a" * 3000
        para2 = "b" * 3000
        chunks = split_whatsapp_text(f"{para1}\n\n{para2}")
        self.assertEqual(chunks, [para1, para2])

    def test_no_content_is_lost(self):
        text = "linha de transcrição do vídeo\n" * 500
        chunks = split_whatsapp_text(text)
        rejoined = " ".join(chunks).split()
        self.assertEqual(rejoined, text.split())

    def test_unbreakable_text_is_hard_cut(self):
        text = "x" * 10000
        chunks = split_whatsapp_text(text)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), WHATSAPP_TEXT_LIMIT)
        self.assertEqual("".join(chunks), text)


if __name__ == "__main__":
    unittest.main()
