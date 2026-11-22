"""Hermetic test entry point: no real credentials, dotenv, or external sockets."""
import os
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["PYTHON_DOTENV_DISABLED"] = "1"
for key in list(os.environ):
    if key.startswith(("WHATSAPP_", "SUPABASE_", "OPENAI_", "GEMINI_", "XAI_", "DATABASE_")):
        del os.environ[key]
from tests.unit.agent._helpers import TEST_ENV
os.environ.update(TEST_ENV)
os.environ["AISHA_LOG_DIR"] = tempfile.mkdtemp(prefix="aisha-test-logs-")


def main():
    def blocked(*args, **kwargs):
        raise RuntimeError("External network is disabled in unit tests")
    with patch.object(socket.socket, "connect", blocked), patch.object(socket.socket, "connect_ex", blocked):
        suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    return not result.wasSuccessful()

if __name__ == "__main__":
    sys.exit(main())
