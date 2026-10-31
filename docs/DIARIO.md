# Diário do projeto

> Registro cronológico de decisões e andamento, para preservar contexto entre sessões.
> Visão geral em [PLANO_MESTRE.md](PLANO_MESTRE.md); detalhe técnico em [PLANO_FASE1.md](PLANO_FASE1.md).

## 31/10/2026

**Decisões:**
- Clone do `whatsapp-chat-viewer` abandonado e removido (parser só Android, saída HTML, mídia processada em silos). Projeto recomeçou do zero nesta pasta.
- Princípios fixados: dado bruto intocado; processamento cronológico com contexto acumulado; conteúdo pesado vira ficha com link; motor separado do canal.
- Estratégia: técnica primeiro (Fase 1), validação com advogados/arquiteto/Verifact depois (Fase 2), produto só com evidência (Fase 3).
- Bot no WhatsApp descartado por ora (política da Meta de jan/2026; exceção do +55 por ordem do CADE é instável).
- Nicho mais promissor na hipótese: jurídico, como complemento do Verifact/ata notarial, nunca prometendo validade judicial (STJ exige cadeia de custódia).

**Feito:**
- `git init`, `.venv` (Python 3.11, sem instalações — etapas 1–3 só usam stdlib), `.gitignore` protegendo `data/` e `output/`.
- Documentação de continuidade em `docs/`.
- **Etapas 1–3 implementadas** (commit `1c1968d`): `extract.py` (zip → pasta), `parser.py` (iPhone + Android, inclusive caracteres invisíveis U+200E e marcadores de mídia em pt/en), `inventory.py` (relatório), `dossier.py` (conversa.md v0 com ids estáveis), CLI (`inventory` e `dossier`). 18 testes sintéticos passando.
- **Nível 0 pronto**: `build` gera `conversa.html` com imagens, players de áudio e vídeo, links de PDF e id citável por mensagem. Sem IA. Ideias de preço em `docs/log.md`.
- **Níveis 1–3 prontos e rodados no exemplo real**: 57/57 áudios transcritos (opus → mp3 via ffmpeg, porque a API recusa .opus), 114 mídias comentadas com a conversa inteira como contexto, análise com resumo/linha do tempo/valores/compromissos/pendências citando ids de mensagem (validação descartou 1 citação inventada). Saídas: `conversa.html` (camadas ligáveis; botão desabilitado quando a camada não existe), `conversa.md` + `anexos/doc-NNN.md` para IA, `custos.json`. Custo total do exemplo: **US$ 0,66** (~39 s com 10 chamadas paralelas). Instalados `openai` e `pymupdf` na `.venv` com aviso prévio.

**Material de teste:**
- Pasta `conversas_brutas/` (fora do Git). Guia em `conversas_brutas/guia.txt`.
- Primeira exportação (zip de 3,1 MB, depois apagada): 610 mensagens (405 Emanuella / 205 Rodrigo), 35 arquivos, 155 mídias omitidas.
- Segunda exportação, pasta `WhatsApp Chat - Emanuella Paiva Corretora de planos/` (14,5 MB): 398 mensagens (254 / 144), mesmo período 22/09–31/10, 115 arquivos e **zero** mídias omitidas (57 áudios, 50 imagens, 7 PDFs, 1 vídeo). O parser leu todas as linhas. A queda de 610 para 398 está no `_chat.txt` que o WhatsApp gerou, não num erro nosso.

**Pendências:**
- Avaliação da Fase 1 (etapa 7): 10 perguntas de resposta conhecida, `.txt` bruto vs. `conversa.md` no ChatGPT.
- Revisão humana da qualidade: transcrições (há erros pontuais, ex. "Prigo eu spartei"), comentários e análise.
- (Opcional) exportar uma conversa de Android e um grupo.
- Fase 2: agendar conversas com advogados do jurídico.
