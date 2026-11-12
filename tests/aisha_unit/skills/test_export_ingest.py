import io
import unittest
import zipfile
from unittest.mock import patch

from aisha.chat_export import ingest

IOS = "[01/11/2026, 10:00:00] Ana: Oi\nsegunda linha\n[01/11/2026, 10:01:00] Bia: áudio omitido"
ANDROID = "01/11/2026, 10:00 - Ana: Oi\n01/11/2026, 10:01 - Mensagem de sistema"


def make_zip(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


class IngestTests(unittest.TestCase):
    def test_platforms_and_multiline(self):
        for text in (IOS, ANDROID):
            with patch.object(
                zipfile.ZipFile, "extractall", side_effect=AssertionError
            ):
                messages = ingest.ingest_zip(
                    make_zip({"_chat.txt": text, "../audio.opus": b"ignored"})
                )
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["sender"], "Ana")
        self.assertEqual(messages[1]["sender"], "[sistema]")
        self.assertIn(
            "\nsegunda linha",
            ingest.ingest_zip(make_zip({"_chat.txt": IOS}))[0]["text"],
        )

    def test_duplicates_stable(self):
        data = make_zip(
            {"chat.txt": ANDROID.splitlines()[0] + "\n" + ANDROID.splitlines()[0]}
        )
        messages = ingest.ingest_zip(data)
        self.assertEqual(messages[1]["id"], messages[0]["id"] + "-1")
        self.assertEqual(messages, ingest.ingest_zip(data))

    def test_reject_invalid_missing_ambiguous(self):
        for data in (
            b"not zip",
            make_zip({"x.txt": "hello"}),
            make_zip({"a.txt": IOS, "b.txt": ANDROID}),
        ):
            with self.assertRaises(ingest.ExportError):
                ingest.ingest_zip(data)

    def test_limits(self):
        data = make_zip({"chat.txt": IOS})
        for name, value in [
            ("MAX_ZIP_BYTES", 1),
            ("MAX_TEXT_BYTES", 1),
            ("MAX_CONTEXT_CHARS", 1),
            ("MAX_ENTRIES", 0),
        ]:
            with (
                patch.object(ingest, name, value),
                self.assertRaises(ingest.ExportError),
            ):
                ingest.ingest_zip(data)

    def test_encrypted(self):
        data = bytearray(make_zip({"chat.txt": IOS}))
        start = data.index(b"PK\x01\x02")
        data[start + 8] |= 1
        with self.assertRaisesRegex(ingest.ExportError, "senha"):
            ingest.ingest_zip(bytes(data))
