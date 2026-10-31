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
- **Nível 0 pronto**: `build` gera `conversa.html` com imagens, players de áudio e vídeo, links de PDF e id citável por mensagem. Sem IA. Camadas de transcrição, comentário e análise já têm botão, mas ficam vazias até a próxima iteração. Ideias de preço em `docs/log.md`.

**Material de teste:**
- Pasta `conversas_brutas/` (fora do Git). Guia em `conversas_brutas/guia.txt`.
- Primeira exportação (zip de 3,1 MB, depois apagada): 610 mensagens (405 Emanuella / 205 Rodrigo), 35 arquivos, 155 mídias omitidas.
- Segunda exportação, pasta `WhatsApp Chat - Emanuella Paiva Corretora de planos/` (14,5 MB): 398 mensagens (254 / 144), mesmo período 22/09–31/10, 115 arquivos e **zero** mídias omitidas (57 áudios, 50 imagens, 7 PDFs, 1 vídeo). O parser leu todas as linhas. A queda de 610 para 398 está no `_chat.txt` que o WhatsApp gerou, não num erro nosso.

**Pendências:**
- Nível 1 (transcrição) ainda não começou. A chave está no `.env`, que não entra no Git.
- (Opcional) exportar uma conversa de Android e um grupo.
- Fase 2: agendar conversas com advogados do jurídico.
