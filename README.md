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
PYTHONPATH=src python -m wa_dossier inventory "conversas_brutas/1_whatsapp_chat_emanuella_paiva_corretora_de_planos.zip"

# Conversa legível em HTML, sem IA (nível 0)
PYTHONPATH=src python -m wa_dossier build "conversas_brutas/WhatsApp Chat - Nome" --me "Seu Nome"
```

As exportações reais ficam em `conversas_brutas/` e as saídas em `output/` — ambas fora do Git.

## Testes

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```
