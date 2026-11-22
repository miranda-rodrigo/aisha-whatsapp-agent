"""Testes do parser com amostras sintéticas (nunca dados reais)."""

import sys
import unittest
from pathlib import Path



from aisha_chat.ingest import build_message_ids  # noqa: E402
from aisha_chat.parser import classify_media, parse_chat  # noqa: E402

LRM = "\u200e"

IOS_SAMPLE = f"""\
[22/09/2026, 01:11:23] {LRM}Maria Corretora: Olá João! 👋

Me chamo Maria e vou te ajudar.
[22/09/2026, 09:48:02] Maria Corretora: bom dia João
[29/09/2026, 13:31:45] João Silva: olá
[29/09/2026, 13:34:00] {LRM}João Silva: {LRM}Voice call. {LRM}2 min
[29/09/2026, 13:44:10] Maria Corretora: valores *BEST SENIOR* {LRM}image omitted
[29/09/2026, 13:45:00] Maria Corretora: {LRM}<attached: 00000028-PHOTO-2026-09-29.jpg>
[29/09/2026, 13:46:00] Maria Corretora: {LRM}<anexado: 00000029-AUDIO-2026-09-29.opus>
[29/09/2026, 13:47:00] {LRM}As mensagens são protegidas com a criptografia de ponta a ponta.
"""

ANDROID_SAMPLE = """\
22/09/2026 01:11 - Maria Corretora: Olá João!
Tudo bem?
22/09/2026 09:48 - João Silva: bom dia
29/09/2026 13:45 - Maria Corretora: IMG-20260929-WA0001.jpg (file attached)
29/09/2026 13:46 - Maria Corretora: <Media omitted>
29/09/2026 13:47 - As mensagens e as ligações são protegidas com a criptografia.
"""


class TestIosParser(unittest.TestCase):
    def setUp(self):
        self.result = parse_chat(IOS_SAMPLE)

    def test_platform(self):
        self.assertEqual(self.result.platform, "ios")

    def test_all_lines_parsed(self):
        self.assertEqual(self.result.unparsed_lines, [])

    def test_message_count(self):
        self.assertEqual(len(self.result.messages), 8)

    def test_multiline(self):
        first = self.result.messages[0]
        self.assertIn("Me chamo Maria", first.text)
        self.assertEqual(first.sender, "Maria Corretora")
        self.assertEqual(first.time, "01:11:23")

    def test_invisible_chars_stripped_from_sender(self):
        call = self.result.messages[3]
        self.assertEqual(call.sender, "João Silva")

    def test_omitted_image(self):
        msg = self.result.messages[4]
        self.assertEqual(msg.omitted_media, ["image"])

    def test_attachment_en(self):
        msg = self.result.messages[5]
        self.assertEqual(msg.attachments, ["00000028-PHOTO-2026-09-29.jpg"])

    def test_attachment_pt(self):
        msg = self.result.messages[6]
        self.assertEqual(msg.attachments, ["00000029-AUDIO-2026-09-29.opus"])

    def test_system_message(self):
        last = self.result.messages[7]
        self.assertTrue(last.is_system)
        self.assertIn("criptografia", last.text)


class TestAndroidParser(unittest.TestCase):
    def setUp(self):
        self.result = parse_chat(ANDROID_SAMPLE)

    def test_platform(self):
        self.assertEqual(self.result.platform, "android")

    def test_all_lines_parsed(self):
        self.assertEqual(self.result.unparsed_lines, [])

    def test_message_count(self):
        self.assertEqual(len(self.result.messages), 5)

    def test_multiline(self):
        self.assertIn("Tudo bem?", self.result.messages[0].text)

    def test_attachment(self):
        msg = self.result.messages[2]
        self.assertEqual(msg.attachments, ["IMG-20260929-WA0001.jpg"])

    def test_media_omitted(self):
        msg = self.result.messages[3]
        self.assertEqual(msg.omitted_media, ["media"])

    def test_system_message(self):
        self.assertTrue(self.result.messages[4].is_system)


class TestHelpers(unittest.TestCase):
    def test_classify_media(self):
        self.assertEqual(classify_media("a.opus"), "audio")
        self.assertEqual(classify_media("b.JPG"), "image")
        self.assertEqual(classify_media("c.mp4"), "video")
        self.assertEqual(classify_media("d.pdf"), "pdf")
        self.assertEqual(classify_media("e.docx"), "file")

    def test_message_ids_unique_for_duplicates(self):
        sample = (
            "22/09/2026 10:00 - Ana: oi\n"
            "22/09/2026 10:00 - Ana: oi\n"
        )
        result = parse_chat(sample)
        ids = build_message_ids(result.messages)
        self.assertEqual(len(ids), 2)
        self.assertNotEqual(ids[0], ids[1])
        self.assertTrue(ids[1].startswith(ids[0]))


if __name__ == "__main__":
    unittest.main()
