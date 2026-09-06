#!/usr/bin/env python3
"""Gera variantes denoised do áudio com chuveiro para comparação.

Uso:
    python denoise.py ENTRADA.wav DIR_SAIDA

Saída: WAV mono 16 kHz em DIR_SAIDA/<variante>.wav (formato nativo do Whisper).

Dependências:
    - ffmpeg com os filtros afftdn e arnndn
    - pip install noisereduce soundfile numpy
    - modelo RNNoise (.rnnn) de https://github.com/GregorR/rnnoise-models
      -> RNNOISE_MODEL (padrão: /tmp/rnn/sh.rnnn)
    - binário deep-filter (DeepFilterNet3, Rust) das releases de
      https://github.com/Rikorose/DeepFilterNet -> DEEP_FILTER_BIN (padrão: /tmp/deep-filter)
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import soundfile as sf

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
RNN_MODEL = os.environ.get("RNNOISE_MODEL", "/tmp/rnn/sh.rnnn")
DEEP_FILTER = os.environ.get("DEEP_FILTER_BIN", "/tmp/deep-filter")
# Janela só-ruído dentro do trecho de chuveiro forte (medida por RMS mínimo em 86–318 s).
NOISE_CLIP = (221.0, 222.5)


def run(cmd):
    t = time.time()
    subprocess.run(cmd, check=True, capture_output=True)
    return time.time() - t


def ff(name, af):
    out = OUT / f"{name}.wav"
    dt = run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(SRC),
              "-af", af, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(out)])
    print(f"{name:<32} {dt:6.1f}s  af={af}")


def to16k(src, dst):
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)])


# 0) referência: só reamostrado
ff("00-original", "anull")

# 1) passa-alta + FFT denoiser (ffmpeg afftdn, perfil de ruído branco, sem tracking)
ff("01-afftdn", "highpass=f=90,afftdn=nf=-20:nr=40:nt=w")

# 2) RNNoise (ffmpeg arnndn, modelo somnolent-hogwash) — exige 48 kHz
ff("02-rnnoise", f"highpass=f=90,aresample=48000,arnndn=m={RNN_MODEL}:mix=1")

# 3/4) noisereduce (spectral gating, mesmo princípio do Noise Reduction do Audacity)
import noisereduce as nr  # noqa: E402

y, sr = sf.read(SRC, dtype="float32")
n0, n1 = (int(NOISE_CLIP[0] * sr), int(NOISE_CLIP[1] * sr))
t = time.time()
y_st = nr.reduce_noise(y=y, sr=sr, y_noise=y[n0:n1], stationary=True,
                       prop_decrease=0.9, n_fft=1024, freq_mask_smooth_hz=300,
                       time_mask_smooth_ms=40)
sf.write(OUT / "_tmp_st.wav", y_st, sr)
to16k(OUT / "_tmp_st.wav", OUT / "03-noisereduce-stationary.wav")
print(f"{'03-noisereduce-stationary':<32} {time.time()-t:6.1f}s  prop_decrease=0.9 noise_clip={NOISE_CLIP}")

t = time.time()
y_ns = nr.reduce_noise(y=y, sr=sr, stationary=False, prop_decrease=0.9,
                       n_fft=1024, time_constant_s=2.0, freq_mask_smooth_hz=300,
                       time_mask_smooth_ms=40)
sf.write(OUT / "_tmp_ns.wav", y_ns, sr)
to16k(OUT / "_tmp_ns.wav", OUT / "04-noisereduce-nonstationary.wav")
print(f"{'04-noisereduce-nonstationary':<32} {time.time()-t:6.1f}s  prop_decrease=0.9 time_constant=2s")

# 5/6) DeepFilterNet3 (48 kHz): atenuação total e limitada a 20 dB
#      (-a 20 mistura sinal limpo com o ruidoso ≈ "observation addition", menos artefatos p/ ASR)
run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(SRC),
     "-af", "highpass=f=90", "-ar", "48000", "-ac", "1", str(OUT / "_tmp_48k.wav")])
for name, extra in (("05-deepfilternet3", []), ("06-deepfilternet3-atten20", ["-a", "20"])):
    d = OUT / f"_dfn_{name}"
    d.mkdir(exist_ok=True)
    t = time.time()
    subprocess.run([DEEP_FILTER, "-D", "-o", str(d), *extra, str(OUT / "_tmp_48k.wav")],
                   check=True, capture_output=True)
    produced = next(d.glob("*.wav"))
    to16k(produced, OUT / f"{name}.wav")
    produced.unlink()
    d.rmdir()
    print(f"{name:<32} {time.time()-t:6.1f}s  {' '.join(extra) or 'atenuação total'}")

# 7) cascata: RNNoise seguido de afftdn leve
ff("07-rnnoise+afftdn", f"highpass=f=90,aresample=48000,arnndn=m={RNN_MODEL},afftdn=nf=-35:nr=10:tn=1")

for p in OUT.glob("_tmp*"):
    p.unlink()
print("ok")
