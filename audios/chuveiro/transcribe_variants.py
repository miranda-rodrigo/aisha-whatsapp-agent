#!/usr/bin/env python3
"""Transcreve cada variante de áudio com faster-whisper (CPU, int8).

Uso:
    python transcribe_variants.py DIR_WAVS DIR_SAIDA [MODELO] [--anti-alucinacao] [nome-variante ...]

Saída: DIR_SAIDA/<variante>/raw.txt, raw.srt, meta.json (raw.txt nunca é sobrescrito).

Dependência: pip install faster-whisper
"""
import json
import sys
import time
from pathlib import Path

from faster_whisper import WhisperModel

args = [a for a in sys.argv[1:] if not a.startswith("--")]
ANTI_HALLUCINATION = "--anti-alucinacao" in sys.argv
SRC_DIR = Path(args[0])
OUT_DIR = Path(args[1])
MODEL = args[2] if len(args) > 2 else "large-v3-turbo"
only = args[3:]

BASE_OPTS = dict(
    language="pt",
    beam_size=5,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 300},
    condition_on_previous_text=False,
)
# Configuração para conter loops/alucinações do Whisper em trechos de SNR muito baixo.
ANTI_OPTS = dict(
    initial_prompt="Conversa informal em português do Brasil, gravada num banheiro com o chuveiro ligado.",
    compression_ratio_threshold=2.0,
    log_prob_threshold=-0.8,
    no_speech_threshold=0.5,
    repetition_penalty=1.15,
    hallucination_silence_threshold=2.0,
    word_timestamps=True,
)


def ts(sec):
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


opts = {**BASE_OPTS, **(ANTI_OPTS if ANTI_HALLUCINATION else {})}
model = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=4)
for wav in sorted(SRC_DIR.glob("*.wav")):
    name = wav.stem
    if only and name not in only:
        continue
    out = OUT_DIR / name
    out.mkdir(parents=True, exist_ok=True)
    if (out / "raw.txt").exists():
        print(f"{name}: raw.txt já existe, pulando")
        continue
    t0 = time.time()
    segments, info = model.transcribe(str(wav), **opts)
    lines, srt = [], []
    for i, s in enumerate(segments, 1):
        text = s.text.strip()
        if not text:
            continue
        lines.append(text)
        srt.append(f"{i}\n{ts(s.start)} --> {ts(s.end)}\n{text}\n")
    dt = time.time() - t0
    (out / "raw.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "raw.srt").write_text("\n".join(srt) + "\n", encoding="utf-8")
    words = sum(len(l.split()) for l in lines)
    meta = {
        "source": wav.name,
        "method": f"faster-whisper {MODEL} (cpu, int8), language=pt, beam=5, vad_filter"
        + (", initial_prompt pt-BR, anti-alucinação" if ANTI_HALLUCINATION else ""),
        "duration": info.duration,
        "segments": len(lines),
        "words": words,
        "elapsed_s": round(dt, 1),
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name:<32} segs={len(lines):3d} words={words:4d} {dt:6.1f}s", flush=True)
print("done")
