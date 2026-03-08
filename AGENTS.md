# AGENTS.md

## Cursor Cloud specific instructions

### Overview

WhatsApp Personal Agent — a single-service Python 3.12 FastAPI app that acts as a WhatsApp webhook server. It echoes text messages and transcribes audio via OpenAI Whisper. See `README.md` for full architecture and Meta Business Platform setup details.

### Running the app

```bash
source .venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The app requires a `.env` file with these variables (it calls `sys.exit(1)` if any required var is missing):

| Variable | Required | Notes |
|---|---|---|
| `WHATSAPP_TOKEN` | Yes | Meta Cloud API access token |
| `WHATSAPP_PHONE_ID` | Yes | Phone Number ID |
| `WEBHOOK_VERIFY_TOKEN` | Yes | Webhook verification token |
| `OPENAI_API_KEY` | Yes | For Whisper + GPT-4o-mini |
| `ALLOWED_NUMBERS` | No | Comma-separated; no messages processed without it |
| `PORT` | No | Defaults to 8000 |

For local dev without real credentials, use dummy values — the app starts and processes webhook logic correctly; only outbound calls to Meta/OpenAI will fail (401).

### Linting

No project-level linting config exists. Use `ruff check .` (installed in the venv) for basic Python linting.

### Testing

No automated test suite exists. Test manually with curl against the webhook endpoints:

```bash
# Webhook verification
curl -s "http://localhost:8000/webhook?hub.mode=subscribe&hub.challenge=123&hub.verify_token=$WEBHOOK_VERIFY_TOKEN"

# Simulate text message
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"id":"wamid.test","from":"5500000000000","type":"text","text":{"body":"test"}}]}}]}]}'
```

### System dependencies

- **ffmpeg** and **ffprobe** are required for audio transcription. Pre-installed on the Cloud VM via `apt-get`.
- **python3.12-venv** must be installed for venv creation (`sudo apt-get install -y python3.12-venv`).

### Gotchas

- `config.py` runs at import time and exits immediately if env vars are missing. Always ensure `.env` exists before importing any module.
- The `.env` file is in `.gitignore` — each dev environment needs its own.
- Hot-reload (`--reload` flag) works well; no need to restart after code changes.
