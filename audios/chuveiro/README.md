# Áudio com ruído de chuveiro — filtragem e transcrição

Cópia dos dois arquivos do Google Drive, pesquisa das tecnologias de remoção de ruído estacionário, comparação prática de 7 pipelines de denoise e transcrição de cada variante com Whisper.

## Arquivos

| Arquivo | Origem | Formato | Duração |
|---|---|---|---|
| `2026_09_06_08_05_59-1.wav` | Drive `1QNyGSon4nQ2w7Zyp8eDQvtZk1eORfWn7` | PCM 16 bit, mono, 44,1 kHz (38 MB) | 7 min 12 s |
| `2026_09_06_08_05_59.mp3` | Drive `1eOWAhN54Y67IhJSUoJcbXE2vTiIziOSH` | MP3 128 kbps, mono, 48 kHz (6,9 MB) | 7 min 12 s |

Os dois arquivos são **a mesma gravação** (correlação cruzada 0,978 com lag zero). O WAV é a fonte sem perdas e foi usado como entrada de todos os processamentos.

Outras pastas:

- `denoised/` — versões filtradas (MP3 96 kbps) com RNNoise e DeepFilterNet3, para ouvir a diferença.
- `transcripts/<modelo>/<variante>/raw.txt|raw.srt|meta.json` — transcrições brutas do Whisper, uma por variante de áudio. `raw.txt` nunca foi editado.
- `denoise.py` e `transcribe_variants.py` — scripts usados (ver "Como reproduzir").

## Diagnóstico do ruído

Espectrograma do WAV completo (`showspectrumpic` do ffmpeg, ver `espectrograma-original.webp`; comparação entre filtros no trecho 200–240 s em `espectrogramas-comparacao.webp`):

- **0 s – 86 s**: chuveiro em segundo plano (ruído banda larga moderado).
- **86 s – 318 s**: chuveiro **forte**, ruído branco/rosa denso até 20 kHz. Nesse trecho a mediana de RMS em janelas de 0,5 s é −27 dBFS e o percentil 95 (picos de fala) é −23 dBFS: a fala fica só **~4 a 12 dB acima do ruído**.
- **318 s – 432 s**: volta ao patamar moderado.

Logo o ruído é banda larga, quase estacionário dentro de cada regime, mas com uma mudança abrupta de nível (chuveiro abrindo/fechando). Isso favorece métodos **adaptativos** (RNNoise, DeepFilterNet, afftdn com tracking) sobre um perfil fixo de ruído único (Audacity/noisereduce estacionário), que fica ou fraco no trecho forte ou agressivo demais nos trechos moderados.

## Tecnologias pesquisadas

### 1. Métodos clássicos (DSP)

| Ferramenta | Princípio | Quando usar |
|---|---|---|
| **Audacity → Noise Reduction** | Spectral gating: aprende o perfil do ruído em um trecho só-ruído e atenua bins abaixo do limiar por banda | Ruído constante (hiss, ventilador, água). Grátis. Precisa de trecho só-ruído |
| **noisereduce** (Python) | Mesmo algoritmo do Audacity (`stationary=True` com clipe de ruído) ou limiar adaptativo (`stationary=False`) | Automação em lote; `prop_decrease` 0,8–0,9 evita som "metálico" |
| **iZotope RX — Spectral De-noise** | Subtração espectral com perfil aprendido + modo adaptativo; controles separados p/ tonal e banda larga | Padrão da indústria em pós-produção; pago |
| **ffmpeg `afftdn`** | Denoiser FFT com piso de ruído (`nf`), redução (`nr`), tipo de ruído (`nt=w` branco) e tracking opcional (`tn`) | Linha de comando, sem dependências; precisa ajuste manual |
| **ffmpeg `anlmdn`** | Non-local means no domínio do tempo | Ruído fraco; ineficaz aqui (ver tabela) |
| Filtro passa-alta 80–100 Hz | Remove ronco/rumble abaixo da voz | Sempre, custo zero |

Limitação comum: geram *musical noise* (artefatos "aquáticos") quando o SNR é baixo e não distinguem fala de ruído — só nível.

### 2. Redes neurais de speech enhancement (estado da arte 2025-2026)

| Modelo | Arquitetura | Latência / custo | Licença | Observações |
|---|---|---|---|---|
| **RNNoise** (Xiph/Mozilla, 2017; embutido no ffmpeg como `arnndn`) | DSP + 3 camadas GRU, ganho em 22 bandas; 85 KB | ~10 ms, roda em qualquer CPU | BSD | Muito bom em ruído estável (ventilador, água); pior em ruído não estacionário |
| **DeepFilterNet3** (Uni. Erlangen, 2023–2026) | Deep filtering full-band em duas etapas (ERB + filtro complexo) ; 2,1 M parâmetros | ~40 ms, RTF 0,19 em laptop | MIT / Apache-2.0 | Melhor qualidade open-source; PESQ 3,5–4,0, STOI > 0,95. Binário Rust `deep-filter` sem PyTorch |
| **Demucs / facebook `denoiser`** | Encoder-decoder na forma de onda; 33 M parâmetros | pesado (7,7 GMAC/s) | MIT (código) | Boa qualidade, muito mais compute; pouco vantajoso frente ao DFN3 |
| **FullSubNet+** | Full-band + sub-band com atenção temporal | pesado | MIT | Destaque no DNS Challenge |
| **Resemble Enhance** | Denoise + *enhance* generativo (difusão) | GPU | MIT | Reconstrói a voz; ótimo para ouvir, mas pode "inventar" fonemas — perigoso antes de ASR |
| **Adobe Podcast Enhance / Adobe Audition** | Nuvem, generativo | on-line | Comercial | Excelente para publicar áudio; não recomendado como pré-processamento de transcrição |
| **Krisp SDK / NVIDIA Broadcast (Maxine)** | Supressores em tempo real | ~25 ms / GPU RTX | Comercial | Voltados para chamadas ao vivo |

Consenso das comparações (Sinergi 2025, Interspeech 2024, benchmarks de 2026): **DeepFilterNet3 é o melhor open-source em qualidade**; RNNoise é o melhor custo-benefício para ruído estável em tempo real.

### 3. Denoise antes do Whisper: nem sempre ajuda

Três estudos recentes mostram um resultado contra-intuitivo:

- *When De-noising Hurts* (arXiv 2512.17562, dez/2025): denoising MetricGAN+ **piorou** o WER de Whisper, Parakeet, Gemini Flash e Parrotlet em 40/40 configurações (+1,1 a +46,6 pontos).
- *When Denoising Hinders* (arXiv 2603.04710, mar/2026): SAM-Audio melhora PSNR e a percepção humana mas **aumenta WER/CER do Whisper**, e quanto maior o modelo Whisper, pior.
- *Rethinking Processing Distortions* (arXiv 2404.14860): os **artefatos** do enhancement, não o ruído residual, são o que degrada o ASR; misturar sinal limpo com o ruidoso (*observation addition*) recupera parte da acurácia.

Motivo: Whisper foi treinado com 680 k h de áudio ruidoso e já é robusto a ruído; artefatos espectrais são fora da distribuição de treino. A recomendação prática é **transcrever o original e as versões filtradas e comparar**, e preferir filtros com atenuação limitada (por exemplo `deep-filter -a 20`) quando o objetivo é ASR e não audição humana.

## O que foi executado

Todas as variantes saem em WAV mono 16 kHz (`denoise.py`):

| Variante | Pipeline | Tempo (CPU 4 núcleos) |
|---|---|---|
| `00-original` | só reamostragem | 0,3 s |
| `01-afftdn` | `highpass=f=90, afftdn=nf=-20:nr=40:nt=w` | 1,5 s |
| `02-rnnoise` | `highpass, aresample=48000, arnndn=m=sh.rnnn` | 3,1 s |
| `03-noisereduce-stationary` | spectral gating, perfil de ruído em 221,0–222,5 s, `prop_decrease=0.9` | 3,9 s |
| `04-noisereduce-nonstationary` | spectral gating adaptativo, `time_constant_s=2` | 4,1 s |
| `05-deepfilternet3` | `deep-filter -D` (atenuação total) | 55 s |
| `06-deepfilternet3-atten20` | `deep-filter -D -a 20` (limita atenuação a 20 dB, mistura com o original) | 56 s |
| `07-rnnoise+afftdn` | RNNoise seguido de afftdn leve | 4,1 s |

Redução de ruído medida (RMS em janelas só-ruído; "SNR≈" = p95 dos quadros de 0,5 s no trecho forte menos o piso de ruído do trecho forte):

| Variante | Piso ruído trecho fraco | Piso ruído trecho forte | Pico de fala trecho forte | SNR≈ |
|---|---|---|---|---|
| `00-original` | −36,7 dB | −34,6 dB | −23,0 dB | 11,6 dB |
| `01-afftdn` | −38 a −49 dB* | −49,3 dB* | −24,8 dB | 24,5 dB |
| `02-rnnoise` | −46,7 dB | −54,5 dB | −29,8 dB | 24,7 dB |
| `03-noisereduce-stationary` | −50,4 dB | −49,6 dB | −24,7 dB | 24,9 dB |
| `04-noisereduce-nonstationary` | −56,6 dB | −54,6 dB | −30,6 dB | 24,0 dB |
| `05-deepfilternet3` | −66,8 dB | **−79,5 dB** | −29,2 dB | **50,4 dB** |
| `06-deepfilternet3-atten20` | −56,3 dB | −56,0 dB | −28,7 dB | 27,3 dB |
| `07-rnnoise+afftdn` | −46,9 dB | −56,4 dB | −29,6 dB | 26,8 dB |

\* `afftdn` com `tn=1` (tracking) quase não atuou (−2 dB); só a configuração fixa `nf=-20:nr=40` deu resultado. `anlmdn` não teve efeito mensurável e foi descartado.

Em termos de **audição**, DeepFilterNet3 remove o chuveiro quase por completo; RNNoise e o `-a 20` deixam um resíduo suave e menos artefatos.

## Transcrição

### Bloqueio: chave OpenAI inválida

O fluxo padrão do repositório (skill `transcribe-media` → API `whisper-1`) falhou: o secret `openai key` retorna `401 invalid_api_key` (chave `sk-proj-…48EA`). Testado diretamente com `curl https://api.openai.com/v1/models`. Para não travar a entrega, a transcrição foi feita **localmente** com `faster-whisper` (CTranslate2, CPU int8), modelos `large-v3-turbo` e `large-v3`. Ao atualizar o secret em *Cloud Agents → Secrets*, basta rodar o script da skill sobre os arquivos de `denoised/` para ter a versão `whisper-1`.

### Resultados

| Modelo | Variante | Segmentos | Palavras | Leitura qualitativa |
|---|---|---|---|---|
| large-v3-turbo | 00-original | 61 | 158 | trecho forte vira "e aí / o / …" (alucinação) |
| large-v3-turbo | 01-afftdn | 42 | 146 | loops "Não, não, não" e frases inventadas |
| large-v3-turbo | 02-rnnoise | 19 | 107 | poucos segmentos, mas coerentes |
| large-v3-turbo | 03-noisereduce-stationary | 37 | 160 | razoável no início/fim, perdido no meio |
| large-v3-turbo | 04-noisereduce-nonstationary | 22 | 63 | removeu fala junto com o ruído |
| large-v3-turbo | 05-deepfilternet3 | 83 | 277 | mais conteúdo, porém loops "O que é isso?" ×8 |
| large-v3-turbo | 06-deepfilternet3-atten20 | 66 | 216 | loops "Onde está?" ×10 |
| large-v3-turbo | 07-rnnoise+afftdn | 38 | 82 | pouco conteúdo |
| large-v3 | 00-original | 35 | 174 | **mais coerente**, poucos loops |
| large-v3 | 02-rnnoise | 34 | 143 | coerente, alguns loops |
| large-v3 | 05-deepfilternet3 | 47 | 160 | bom, poucos loops |
| large-v3 | 06-deepfilternet3-atten20 | 78 | 293 | muito conteúdo, mas vários loops |
| large-v3 + anti-alucinação | 00-original | 36 | 147 | limpo, sem loops |
| large-v3 + anti-alucinação | 05-deepfilternet3 | 32 | 120 | limpo; único a acertar "sabonete" |
| large-v3 + anti-alucinação | 06-deepfilternet3-atten20 | 36 | 109 | um loop "E aí" ×9 |

"Anti-alucinação" = `initial_prompt` em pt-BR, `compression_ratio_threshold=2.0`, `log_prob_threshold=-0.8`, `no_speech_threshold=0.5`, `repetition_penalty=1.15`, `hallucination_silence_threshold=2.0`.

### Conclusões

1. **O trecho 86 s – 318 s (chuveiro forte) está abaixo do limiar de inteligibilidade para ASR.** Nenhum filtro recupera a fala nesse trecho: os modelos ou silenciam ou alucinam. Isso confirma o que a literatura descreve — o denoise melhora muito a audição humana (DeepFilterNet3 tira ~45 dB de ruído) mas não cria informação que o microfone não captou.
2. Para **transcrever**, o melhor conjunto foi `large-v3` (modelo completo, não o turbo) com configuração anti-alucinação, aplicado ao **original** e ao **DeepFilterNet3**; os dois se complementam. `large-v3-turbo` alucina muito mais com SNR baixo.
3. Para **ouvir**, use `denoised/05-deepfilternet3.mp3` (mais limpo) ou `denoised/06-deepfilternet3-atten20.mp3` (mais natural).
4. Os filtros baratos (`afftdn`, `noisereduce`) não valem a pena aqui; RNNoise é uma boa opção rápida (3 s de processamento) se DeepFilterNet não estiver disponível.

### Falas reconhecidas de forma consistente

Trechos que aparecem com o mesmo conteúdo em pelo menos três transcrições independentes (original e variantes filtradas, modelos diferentes). Tempo aproximado; o que não está aqui foi transcrito de forma divergente entre variantes e deve ser tratado como **não confiável**.

| Tempo | Fala (leitura consistente) |
|---|---|
| 0:03 | "…mora / moro (bem) aqui, né?" — "É." |
| 0:06 | "Tu vai se molhar/morrer logo?" — "Vou." |
| 0:50 | "Cadê o cabo?" |
| 1:03 | "É 60 watts." — "Quando tem mais é…" / "Pô, não tem mais, né?" |
| 1:18 | "E esse é de sabonete?" — "Sabonete." (ouvido também como "Sabe o leite", "Salve-noite") |
| 2:23 | "Obrigado." |
| ~3:50 | "E a sua água, foi?" — "Ainda não." |
| ~3:58 | "Mas a gente vai ter que fazer (uma) revisão, tá ligado?" |
| ~4:00 | "Pra tirar as fotos…" |
| 4:04–4:10 | "Enfim." — "Tipo assim, não…" |
| 4:15 | "É só assim." |
| 4:34 | "Esqueci, né?" — "Esqueci agora." — "…desligado/desligada." |
| 4:38 | "Sim, é…" |
| 4:40 | "Ah, deve ter afrouxado/arrochado o negócio." |
| 4:51 | "Você não acha que tem que colocar…" |
| 4:59–5:32 | "Olha o Grindr." |
| 5:37–5:52 | "(E aí,) você tá bem?" — "Tô." |
| 6:04 | "Tá triste." |
| 6:11–6:41 | "Vai se molhar, não?" — "Vou (lá)." |

Transcrições brutas completas, com timestamps, em `transcripts/`. Recomendadas para leitura: `transcripts/large-v3-anti-alucinacao/00-original/raw.txt` e `transcripts/large-v3-anti-alucinacao/05-deepfilternet3/raw.txt`.

## Como reproduzir

```bash
# ambiente isolado (não usa o .venv do projeto)
python3 -m venv /tmp/dn && /tmp/dn/bin/pip install noisereduce soundfile numpy faster-whisper

# modelo RNNoise para o filtro arnndn do ffmpeg
mkdir -p /tmp/rnn && curl -sL -o /tmp/rnn/sh.rnnn \
  https://raw.githubusercontent.com/GregorR/rnnoise-models/master/somnolent-hogwash-2018-09-01/sh.rnnn

# DeepFilterNet3: binário Rust (sem PyTorch). O pacote pip `deepfilternet` 0.5.6 quebra
# com torchaudio >= 2.9 (import de torchaudio.backend removido).
curl -sL -o /tmp/deep-filter \
  https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep-filter-0.5.6-x86_64-unknown-linux-musl
chmod +x /tmp/deep-filter

cd audios/chuveiro
/tmp/dn/bin/python denoise.py 2026_09_06_08_05_59-1.wav /tmp/variants
/tmp/dn/bin/python transcribe_variants.py /tmp/variants transcripts/large-v3-turbo large-v3-turbo
/tmp/dn/bin/python transcribe_variants.py /tmp/variants transcripts/large-v3 large-v3 \
  00-original 02-rnnoise 05-deepfilternet3 06-deepfilternet3-atten20
/tmp/dn/bin/python transcribe_variants.py /tmp/variants transcripts/large-v3-anti-alucinacao large-v3 \
  --anti-alucinacao 00-original 05-deepfilternet3 06-deepfilternet3-atten20
```

Com a chave OpenAI válida, a via oficial do repositório é:

```bash
export OPENAI_API_KEY=...
python .cursor/skills/transcribe-media/scripts/transcribe.py audios/chuveiro/denoised/05-deepfilternet3.mp3 \
  --out audios/chuveiro/transcripts/whisper-1/05-deepfilternet3
```

## Referências

- Schröter et al., *DeepFilterNet3* — https://github.com/Rikorose/DeepFilterNet
- Valin, *RNNoise* — https://jmvalin.ca/demo/rnnoise/ ; modelos: https://github.com/GregorR/rnnoise-models
- Sainburg, *noisereduce* — https://github.com/timsainb/noisereduce
- Audacity Manual, *Noise Reduction* — https://manual.audacityteam.org/man/noise_reduction.html
- iZotope RX 11, *Spectral De-noise* — https://docs.izotope.com/rx11/en/spectral-de-noise.html
- ffmpeg filters `afftdn`, `arnndn`, `anlmdn` — https://ffmpeg.org/ffmpeg-filters.html
- *When De-noising Hurts: A Systematic Study of Speech Enhancement Effects on Modern Medical ASR Systems* — https://arxiv.org/abs/2512.17562
- *When Denoising Hinders: Revisiting Zero-Shot ASR with SAM-Audio and Whisper* — https://arxiv.org/abs/2603.04710
- *Rethinking Processing Distortions: Disentangling the Impact of Speech Enhancement Errors on ASR* — https://arxiv.org/abs/2404.14860
- *Are Recent Deep Learning-Based Speech Enhancement Methods Ready to Confront Real-World Noisy Environments?* (Interspeech 2024) — https://doi.org/10.21437/interspeech.2024-129
- Comparativos 2026: https://noisereducerai.com/blogs/deepfilternet-vs-rnnoise/ ; https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/real-time-noise-suppression-krisp-rnnoise-deepfilternet
