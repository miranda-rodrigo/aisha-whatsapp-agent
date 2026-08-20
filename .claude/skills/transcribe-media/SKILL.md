---
name: transcribe-media
description: Transcribe any video, audio, YouTube/X URL, or existing .txt/.srt/.vtt into a raw transcript, then optionally clean it without AI or improve it with AI. Always keep and show the raw file. Use whenever the user asks to transcribe, transcrever, get captions/legendas, Whisper a file, show the raw vs improved transcript, or turn mp3/mp4/opus/ogg/YouTube/X into text.
---

# Transcribe media

Transcribe video, audio, a URL (YouTube, X, or anything yt-dlp resolves), or an existing transcript file. The raw transcript is the source of truth. Do not beautify it unless the user asked.

## When to use

Use this skill for transcription, captions, Whisper, "texto bruto", "melhora essa transcrição", `.mp4`/`.mp3`/`.opus`/`.srt`/`.vtt`, or a YouTube/X link whose goal is text — not when they only want to download the video file.

## Setup

1. If `.venv` exists in the project, activate it before running scripts.
2. Scripts live next to this file:
   - `scripts/transcribe.py` — always produces `raw.txt` (+ `meta.json`, and `raw.srt` when timestamps exist)
   - `scripts/cleanup.py` — deterministic cleanup, never touches `raw.txt`
   - `references/refine-prompt.md` — editorial prompt for AI improve
3. Need `ffmpeg`/`ffprobe`, `yt-dlp` (URLs), `openai` + `OPENAI_API_KEY` (Whisper). If a script says a dependency is missing, **ask the user before installing**. Do not pip install, brew install, or download models on your own.
4. Do not train or download a local Whisper model.

## Workflow

### 1. Resolve the source

File path, URL in the message, or an attached media/text file. If more than one candidate, ask.

### 2. Transcribe to raw (always)

From the skill directory (or with absolute paths to the scripts):

```bash
python scripts/transcribe.py SOURCE --out transcripts/<slug>
```

This writes:

- `transcripts/<slug>/raw.txt` — never overwrite this later
- `transcripts/<slug>/meta.json` — `source`, `method` (`captions` | `whisper` | `text`), `duration`
- `transcripts/<slug>/raw.srt` — only when timestamps exist

If `raw.txt` already exists in that folder, the script leaves it alone. Pick a new `--out` dir if they want a fresh run.

Read `meta.json`. If the process failed because of a missing tool or key, stop and ask.

### 3. Optional cleanup without AI

Only if they asked to limpar / clean **sem IA** / without AI / "só pontuação":

```bash
python scripts/cleanup.py transcripts/<slug>/raw.txt --out transcripts/<slug>/cleaned.txt
```

This must not modify `raw.txt`. The script is conservative: filler pauses (`uh`, `um`, `hã`, `hmm`) and spacing — not real words like `tipo`, `né`, `então`.

### 4. Optional improve with AI

Only if they asked to melhorar / improve **com IA**. You are the editor — do not call Gemini or an extra API.

1. Read `raw.txt` (the original, not cleaned).
2. Read `references/refine-prompt.md` and follow it.
3. Write the result to `transcripts/<slug>/improved.txt`.
4. Do not replace `raw.txt`. Do not summarize. Keep the original language and approximate length.

### 5. Reply

Always cite the **raw** transcript: a short preview (~80–120 words) plus the full path to `raw.txt`, even when you also deliver cleaned/improved.

Then mention any extra files you created (`cleaned.txt`, `improved.txt`, `raw.srt`).

If the user did not say whether they want raw, cleaned, or AI-improved, deliver the raw preview and ask which they want. If the first message already chose (e.g. "transcreve e melhora com IA"), do that and still show the raw path.

## Defaults

| User said | Do |
|---|---|
| just "transcreve" / "transcribe" | raw only, then ask if they want cleaned or improved |
| "sem IA" / "limpo" / "clean without AI" | raw + `cleanup.py` |
| "com IA" / "melhora" / "improve" | raw + you write `improved.txt` from the refine prompt |
| both / "as duas" | raw + cleaned and/or improved, never delete raw |

Show raw first. Improved is optional extra, not a replacement.
