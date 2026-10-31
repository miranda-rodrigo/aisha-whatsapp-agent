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
- Etapa 1 em andamento: `extract.py`, `parser.py` (iPhone + Android) e testes sintéticos.

**Material de teste disponível:**
- Exportação iPhone "Emanuella Paiva Corretora de planos" (610 msgs, 22/set–31/out/2026, 145 mídias citadas / 35 presentes, ~3,1 MB) — usuário ainda precisa copiar o `.zip` para `data/`.

**Pendências do usuário:**
- Copiar o `.zip` da conversa para `data/`.
- (Opcional) exportar uma conversa de Android e um grupo para ampliar os testes.
- Fase 2: começar a agendar conversas com advogados do jurídico (gargalo é agenda, não código).
