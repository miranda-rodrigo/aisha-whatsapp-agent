#!/usr/bin/env bash
# Cloud Agent bootstrap for the Aisha repository.
# Idempotent: safe to run repeatedly and against cached/snapshot state.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# System packages not guaranteed in the base image.
# python3.12-venv: required to create the backend virtualenv.
# ffmpeg: required by audio transcription (Whisper/yt-dlp conversion).
missing_pkgs=()
dpkg -s python3.12-venv >/dev/null 2>&1 || missing_pkgs+=(python3.12-venv)
command -v ffmpeg >/dev/null 2>&1 || missing_pkgs+=(ffmpeg)
if [ "${#missing_pkgs[@]}" -gt 0 ]; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq "${missing_pkgs[@]}"
fi

# Backend (FastAPI) Python environment.
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Website (Next.js) dependencies.
cd website
pnpm install --frozen-lockfile
