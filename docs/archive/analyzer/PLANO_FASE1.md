# Plano Técnico — Fase 1 (teste técnico)

> Detalha a Fase 1 do [PLANO_MESTRE.md](PLANO_MESTRE.md). Status de cada etapa no [DIARIO.md](DIARIO.md).

## Pré-requisitos

- `.zip` exportado(s) em `data/` (fora do Git; ver `.gitignore`).
- `OPENAI_API_KEY` no ambiente — necessária só a partir da etapa 4.
- `.venv` com Python 3.11. Etapas 1–3 usam apenas a biblioteca padrão (zero instalações).

## Estrutura

```
chat_analysis_whatsapp/
  data/                   # exportações reais (fora do Git)
  output/<chat>/          # dossiês gerados (fora do Git)
  src/wa_dossier/
    extract.py            # abre o .zip, detecta plataforma, lista mídias
    parser.py             # iPhone e Android -> lista de Message
    inventory.py          # relatório de inventário
    transcribe.py         # áudios (etapa 4)
    describe.py           # imagens/PDFs com contexto (etapa 5)
    dossier.py            # gera conversa.md + anexos/*.md
    cli.py                # subcomandos: inventory, dossier
  tests/                  # testes do parser com amostras sintéticas (nunca dados reais)
  docs/                   # este plano + diário
```

Uso: `PYTHONPATH=src python -m wa_dossier <comando>` (ou via `cli.py`).

Dependências previstas para as etapas 4–5 (aprovar antes de instalar): `openai`, `pymupdf`. `ffmpeg` (Homebrew) só se vídeo entrar no escopo.

## Etapas

### 1. Fundação (sem IA, sem custo)
- `extract.py`: abre o zip, encontra `_chat.txt` (iPhone) ou `chat.txt` (Android), lista mídias.
- `parser.py`: dois formatos.
  - iPhone: `[dd/mm/aaaa, hh:mm:ss] Autor: texto`, prefixo invisível U+200E, anexos `<attached: ...>`/`<anexado: ...>`, omitidos `image omitted`/`imagem ocultada` e variantes.
  - Android: `dd/mm/aaaa hh:mm - Autor: texto`, anexos `(file attached)`/`(arquivo anexado)`, omitidos `<Media omitted>`/`<Mídia oculta>`.
  - Multilinha, mensagens de sistema, chamadas de voz.
- Testes com amostras sintéticas nos dois formatos.

### 2. Inventário (sem IA)
- `inventory.py`: mensagens por autor e tipo, período, mídias presentes vs. citadas-mas-omitidas, tamanhos, linhas não parseadas.
- Validar contra o chatview (610 msgs, 145 mídias citadas, 35 presentes).
- **Corte: se não lermos ~100% das mensagens do zip real, parar e corrigir o parser.**

### 3. Dossiê v0 (sem IA)
- `dossier.py`: `output/<chat>/conversa.md` com linha do tempo completa, id estável por mensagem (hash de data+hora+autor+texto, sufixo numérico em colisão) e placeholders de mídia.
- Baseline para a avaliação da etapa 7.

### 4. Transcrição de áudios (primeira etapa com custo)
- API OpenAI (padrão `gpt-4o-mini-transcribe`), cache em arquivo ao lado do áudio (re-rodar não paga de novo), flag `--limit N`.
- Transcrição fiel, nunca alterada por LLM (princípio 1 do plano mestre).
- Medir: custo por minuto e qualidade a olho em 5–10 áudios em português.

### 5. Descrições com contexto (imagens, PDFs)
- Passada única cronológica; contexto acumulado inclui transcrições já feitas e algumas mensagens posteriores à mídia.
- Imagens: 2–3 linhas focadas no objetivo. PDFs: ficha `anexos/doc-NNN.md` (texto integral só se curto). Vídeo: fora da Fase 1 salvo decisão contrária.
- Objetivo do usuário (`--objetivo "..."`) orienta todos os prompts.

### 6. Dossiê v1 completo
- Transcrições inline, descrições curtas com links para fichas, cabeçalho com inventário, cada descrição citando o id da mensagem de origem.

### 7. Avaliação (a pergunta que decide tudo) ← PRÓXIMO PASSO
- 12 perguntas de resposta conhecida sobre a conversa real.
- Comparar ChatGPT com `.txt` bruto vs. PDF do Zap2Doc vs. o dossiê (`output/<chat>/conversa.md`). Registrar acertos, fontes e invenções.
- Protocolo, perguntas e tabela de resultado em [AVALIACAO.md](AVALIACAO.md).
- Resultado alimenta a Fase 2 e a decisão de produto.

> Status 31/10/2026: etapas 1–6 concluídas e rodadas no exemplo real (US$ 0,66, ~39 s).
> Custos detalhados em [log.md](log.md); andamento em [DIARIO.md](DIARIO.md).

## Fora do escopo da Fase 1

Interface web, bot de WhatsApp, PDF para humanos, pagamento, perfil jurídico com numeração de provas, vídeo.
