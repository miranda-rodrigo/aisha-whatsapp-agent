# wa-dossier — Dossiê de Conversas de WhatsApp

Transforma a exportação de uma conversa de WhatsApp (texto + mídias) em um dossiê em Markdown
que uma IA consegue analisar sem perder o contexto das mídias: transcrições fiéis de áudios,
descrições de imagens/PDFs geradas com o contexto da conversa, e citações estáveis por mensagem.

## Documentação

| Documento | Conteúdo |
|---|---|
| [docs/PLANO_MESTRE.md](docs/PLANO_MESTRE.md) | O que é o projeto, princípios, fases, hipótese de negócio, restrições |
| [docs/PLANO_FASE1.md](docs/PLANO_FASE1.md) | Plano técnico detalhado da fase atual |
| [docs/DIARIO.md](docs/DIARIO.md) | Decisões e andamento, em ordem cronológica |

## Uso (Fase 1)

```bash
source .venv/bin/activate

# Inventário da exportação (sem IA, sem custo)
PYTHONPATH=src python -m wa_dossier inventory "data/WhatsApp Chat - Fulano.zip"

# Dossiê v0 (linha do tempo em Markdown, sem IA)
PYTHONPATH=src python -m wa_dossier dossier "data/WhatsApp Chat - Fulano.zip"
```

As exportações reais ficam em `data/` e as saídas em `output/` — ambas fora do Git.

## Testes

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```
