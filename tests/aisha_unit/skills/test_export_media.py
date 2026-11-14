# ruff: noqa: E402
import io
import unittest
import wave
from unittest.mock import patch

from tests.aisha_unit._helpers import configure_test_env

configure_test_env()

from PIL import Image

from aisha.chat_export import media
from aisha.chat_export.ingest import ExportError, ingest_zip
from tests.aisha_unit.skills.test_export_ingest import make_zip


def image_bytes():
    out = io.BytesIO()
    Image.new("RGB", (2000, 900), "#1d4e89").save(out, "PNG")
    return out.getvalue()


def audio_bytes():
    out = io.BytesIO()
    with wave.open(out, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\0\0" * 8000)
    return out.getvalue()


def fixture():
    return make_zip(
        {
            "_chat.txt": "[14/11/2026, 10:00:00] Ana: Veja o defeito.\n[14/11/2026, 10:01:00] Ana: <attached: foto.png>\n[14/11/2026, 10:02:00] Bia: <attached: fala.wav>\n[14/11/2026, 10:03:00] Ana: <attached: livro.pdf>\n",
            "foto.png": image_bytes(),
            "fala.wav": audio_bytes(),
            "livro.pdf": b"not opened",
        }
    )


class MediaIngestTests(unittest.TestCase):
    def test_preflight_ids_and_reduced_image(self):
        data = fixture()
        original = ingest_zip(data)
        messages, files = media.prepare(data)
        self.assertEqual([m["id"] for m in original], [m["id"] for m in messages])
        photo = messages[1]["media"][0]
        with Image.open(io.BytesIO(files[photo["hash"]])) as im:
            self.assertEqual(im.size, (1600, 720))
            self.assertFalse(im.getexif())
        self.assertAlmostEqual(messages[2]["media"][0]["seconds"], 1)
        self.assertEqual(messages[3]["media"][0]["status"], "not_processed")
        self.assertEqual(len(files), 2)

    def test_missing_corrupt_ambiguous_traversal_and_duration(self):
        def zip_for(name, files):
            return make_zip(
                {
                    "_chat.txt": f"[14/11/2026, 10:00:00] Ana: <attached: {name}>\n",
                    **files,
                }
            )

        messages, files = media.prepare(zip_for("missing.png", {}))
        self.assertEqual(messages[0]["media"][0]["status"], "missing")
        messages, _ = media.prepare(zip_for("bad.png", {"bad.png": b"bad"}))
        self.assertEqual(messages[0]["media"][0]["status"], "invalid")
        for name, files in [
            ("../a.png", {}),
            ("a.png", {"one/a.png": b"x", "two/a.png": b"y"}),
        ]:
            with self.assertRaises(ExportError):
                media.prepare(zip_for(name, files))
        with patch.object(media, "MAX_SECONDS", 0.5):
            with self.assertRaisesRegex(ExportError, "60 minutos"):
                media.prepare(fixture())

    def test_android_and_limit(self):
        data = make_zip(
            {
                "chat.txt": "14/11/2026 10:00 - Ana: foto.png (file attached)\n",
                "foto.png": image_bytes(),
            }
        )
        messages, _ = media.prepare(data)
        self.assertEqual(messages[0]["media"][0]["number"], 1)
        with patch.object(media, "MAX_IMAGES", 0):
            with self.assertRaises(ExportError):
                media.prepare(data)
