"""Testes do modelo e da validação de citações, com dados sintéticos."""

import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wa_dossier.context import local_window  # noqa: E402
from wa_dossier.model import (  # noqa: E402
    display_text,
    merge_layers,
    slice_since,
    strip_invalid_citations,
    validate_analise,
)
from wa_dossier.parser import Message  # noqa: E402


def _msg(text: str) -> Message:
    return Message(date="22/09/26", time="10:00", sender="Ana", text=text)


class TestDisplayText(unittest.TestCase):
    def test_removes_ios_attachment_marker(self):
        self.assertEqual(display_text(_msg("<attached: a.jpg>")), "")

    def test_removes_omitted_marker_keeps_caption(self):
        self.assertEqual(display_text(_msg("valores *BEST* image omitted")), "valores *BEST*")

    def test_plain_text_untouched(self):
        self.assertEqual(display_text(_msg("bom dia")), "bom dia")


class TestMergeLayers(unittest.TestCase):
    def test_transcription_survives_rebuild(self):
        old = {"messages": [{"id": "msg-1", "media": [
            {"filename": "a.opus", "transcricao": "olá"}]}],
            "analise": {"resumo": "r"}, "objetivo": "x", "nivel": 3}
        fresh = {"messages": [{"id": "msg-1", "media": [
            {"filename": "a.opus"}]}], "analise": None, "objetivo": "", "nivel": 0}
        merged = merge_layers(fresh, old)
        self.assertEqual(merged["messages"][0]["media"][0]["transcricao"], "olá")
        self.assertEqual(merged["analise"]["resumo"], "r")
        self.assertEqual(merged["objetivo"], "x")


class TestCitations(unittest.TestCase):
    def setUp(self):
        self.ids = {"msg-1", "msg-2"}
        self.analise = {
            "resumo": "r",
            "valores": [
                {"texto": "ok", "mensagens": ["msg-1"]},
                {"texto": "inventado", "mensagens": ["msg-999"]},
                {"texto": "misto", "mensagens": ["msg-2", "msg-999"]},
            ],
        }

    def test_validate_flags_bad_ids(self):
        problems = validate_analise(self.analise, self.ids)
        self.assertTrue(any("msg-999" in p for p in problems))

    def test_strip_removes_fully_invented_claims(self):
        cleaned = strip_invalid_citations(self.analise, self.ids)
        texts = [item["texto"] for item in cleaned["valores"]]
        self.assertEqual(texts, ["ok", "misto"])
        self.assertEqual(cleaned["valores"][1]["mensagens"], ["msg-2"])


class TestSliceSince(unittest.TestCase):
    def test_keeps_from_date_inclusive(self):
        conv = {"messages": [
            {"date": "31/07/26", "text": "antes"},
            {"date": "01/08/26", "text": "no dia"},
            {"date": "02/08/2026", "text": "depois"},
        ]}
        sliced = slice_since(conv, datetime(2026, 8, 1))
        self.assertEqual([m["text"] for m in sliced["messages"]], ["no dia", "depois"])
        self.assertEqual(sliced["recorte"]["mensagens_total"], 3)
        self.assertEqual(len(conv["messages"]), 3)


class TestLocalWindow(unittest.TestCase):
    def setUp(self):
        self.conv = {"messages": [
            {"id": f"msg-{i}", "date": "22/09/26", "time": "10:00", "sender": "Ana",
             "is_system": False, "text": f"texto {i}", "media": []}
            for i in range(20)
        ]}
        self.conv["messages"][10]["media"] = [
            {"filename": "a.opus", "kind": "audio", "transcricao": "olá"}]

    def test_marks_only_target_and_its_transcription(self):
        window = local_window(self.conv, "msg-10", before=2, after=1)
        marked = [line for line in window.splitlines() if line.startswith(">>> ")]
        self.assertEqual(len(marked), 2)
        self.assertIn("msg-10", marked[0])
        self.assertIn("olá", marked[1])

    def test_window_bounds(self):
        window = local_window(self.conv, "msg-10", before=2, after=1)
        self.assertIn("msg-8", window)
        self.assertIn("msg-11", window)
        self.assertNotIn("msg-7", window)
        self.assertNotIn("msg-12", window)

    def test_unknown_id(self):
        self.assertEqual(local_window(self.conv, "msg-999"), "")


if __name__ == "__main__":
    unittest.main()
