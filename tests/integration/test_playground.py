import asyncio
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from aisha_chat import analysis, enrich, media, pdf
from aisha_chat.ingest import ExportError, ingest_zip
from aisha_playground.cli import run


def export(text):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("_chat.txt", text)
    return buf.getvalue()


class PlaygroundTests(unittest.IsolatedAsyncioTestCase):
    def test_agent_prompt_resource_survives_packaging(self):
        from importlib.resources import files
        from aisha import agent
        prompt = files("aisha").joinpath("resources/skills.md").read_text()
        self.assertGreater(len(prompt), 1000)
        self.assertTrue(agent._skills_path.is_file())

    async def test_offline_uses_bot_ingestion_and_never_calls_ai(self):
        from aisha.chat_export import ingest as bot_ingest
        self.assertIs(bot_ingest.ingest_zip, ingest_zip)
        raw = export("[22/11/26, 10:00:00] Ana: Reunião amanhã às 14h\n[22/11/26, 10:01:00] Bia: Confirmado\n")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"export.zip"
            source.write_bytes(raw)
            with patch.object(analysis, "get_client", side_effect=AssertionError("AI called")):
                first, summary = await run(source, Path(tmp)/"runs", make_pdf=False)
                second, _ = await run(source, Path(tmp)/"runs", make_pdf=False)
            self.assertNotEqual(first, second)
            normalized = json.loads((first/"conversation.json").read_text())["messages"]
            self.assertEqual(normalized, media.prepare(raw)[0])
            self.assertEqual(summary["mode"], "offline")
            self.assertFalse(summary["errors"])
            self.assertIn("nenhuma chamada de IA", (first/"conversation.html").read_text())
            self.assertTrue((first/"conversation.md").exists())

    async def test_ai_uses_shared_analysis_with_local_storage(self):
        raw = export("[22/11/26, 10:00:00] Ana: Confirmado amanhã\n")
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"OPENAI_API_KEY": "test"}), patch.object(enrich, "store"), patch.object(enrich, "assets"):
            source = Path(tmp)/"export.zip"; source.write_bytes(raw)
            response = {"claims": [{"text": "Confirmação", "ids": [ingest_zip(raw)[0]["id"]]}]}
            with patch.object(analysis, "analyze_structured", AsyncMock(return_value=response)) as call, patch.object(enrich, "comments", AsyncMock(return_value=[])):
                dest, summary = await run(source, Path(tmp)/"runs", ai=True, make_pdf=False)
            call.assert_awaited_once()
            self.assertTrue((dest/"state.json").exists())
            self.assertFalse(summary["errors"])

    async def test_render_failure_preserves_sources_and_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"export.zip"
            source.write_bytes(export("[22/11/26, 10:00:00] Ana: Olá\n"))
            with patch.object(pdf, "render_pdf", AsyncMock(side_effect=RuntimeError("no browser"))):
                dest, summary = await run(source, Path(tmp)/"runs")
            self.assertTrue((dest/"conversation.json").exists())
            self.assertEqual(summary["errors"], ["pdf: RuntimeError"])

    async def test_invalid_zip_does_not_create_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"export.zip"; source.write_bytes(b"invalid")
            with self.assertRaises(ExportError):
                await run(source, Path(tmp)/"runs", make_pdf=False)
            self.assertFalse((Path(tmp)/"runs").exists())

    def test_offline_cli_runs_without_agent_or_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"export.zip"
            source.write_bytes(export("[22/11/26, 10:00:00] Ana: Olá\n"))
            env = {k: v for k,v in os.environ.items() if not k.startswith(("OPENAI", "SUPABASE", "WHATSAPP", "GEMINI", "XAI"))}
            code = "import sys; from aisha_playground.cli import main; result=main(sys.argv[1:]); assert not any(k=='aisha' or k.startswith('aisha.') for k in sys.modules); raise SystemExit(result)"
            result = subprocess.run([sys.executable,"-c",code,str(source),"--output",str(Path(tmp)/"runs"),"--no-pdf"],env=env,capture_output=True,text=True,cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
