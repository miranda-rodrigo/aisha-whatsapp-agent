# WhatsApp Personal Agent

Agente pessoal via WhatsApp com skills modulares. Online desde 22/02/2026.

## Visão Geral

Um agente que roda no WhatsApp Business API (Meta Cloud API) e responde apenas a mensagens dos números autorizados. Funciona como um assistente pessoal com skills que podem ser adicionadas incrementalmente.

## Skills Planejadas

### Fase 1 — Hello World ✅
- Receber e responder mensagens de texto simples via WhatsApp
- Filtro por número (só responde a números autorizados)

### Fase 2 — Transcrição de Áudio (código pronto, aguardando teste)
- Receber áudios encaminhados
- Transcrever usando OpenAI Whisper API
- Responder com o texto transcrito

### Fase 3 — Gym Companion
- Receber foto do exercício/máquina na academia
- LLM identifica o exercício e confirma com o usuário
- Registrar pesos e repetições
- Manter catálogo pessoal de exercícios (evitar nomes duplicados)
- Mostrar histórico e evolução de carga

### Fase 4 — Google Calendar
- Interpretar comandos em linguagem natural ("agenda reunião com João amanhã às 15h")
- Criar eventos no Google Calendar via API

### Fase 5 — Google Contacts
- Salvar contatos via comando no WhatsApp
- Integração com Google People API

### Fases futuras
- Resumir textos/artigos
- Tradução
- Lembretes
- Consulta de emails
- Buscas na web

## Arquitetura

```
whatsapp-agent/
├── app.py              # FastAPI: webhook + envio de mensagens
├── transcribe.py       # Transcrição de áudio via Whisper API
├── config.py           # Settings via environment variables
├── Dockerfile          # Python 3.12 + ffmpeg
├── .dockerignore       # Impede .env de ir pro container
├── requirements.txt    # Dependências Python
├── .env                # Variáveis locais (não vai pro deploy)
├── .gitignore
└── README.md
```

## Stack

- **Python 3.12** + **FastAPI** + **uvicorn**
- **WhatsApp Business API** (Meta Cloud API) — gratuito para service messages
- **OpenAI Whisper API** — transcrição de áudio (~$0.006/min)
- **ffmpeg** — conversão de formatos de áudio
- **Railway** — hosting (Docker), URL: `whatsapp-agent-production-9d0d.up.railway.app`
- **httpx** — HTTP client async

## Setup — Meta Business Platform

### Conta
- **Meta Business Portfolio:** Price Pulse (consultoria com CNPJ ativo)
- **App:** Gym (developers.facebook.com)
- **Use case:** Connect with customers through WhatsApp

### Credenciais
- **Número do agente:** +55 85 9413-2222 (a Meta normaliza removendo um 9 de números BR)
- **Phone Number ID:** `1018015604729721`
- **WhatsApp Business Account ID:** `1265667928785504`
- **Access Token:** token permanente configurado no Railway

### Variáveis de ambiente (Railway)
| Variável | Descrição |
|---|---|
| `WHATSAPP_TOKEN` | Token permanente da API do WhatsApp |
| `WHATSAPP_PHONE_ID` | Phone Number ID do número do agente |
| `WEBHOOK_VERIFY_TOKEN` | Token de verificação do webhook |
| `OPENAI_API_KEY` | Chave da API OpenAI |
| `ALLOWED_NUMBERS` | Números autorizados (separados por vírgula) |
| `PORT` | Porta do servidor (Railway injeta automaticamente) |

### Lições aprendidas no setup
- O número **precisa ser registrado** via API (`POST /{phone-number-id}/register`) após ser adicionado no painel — a UI do Meta não faz isso automaticamente.
- O app precisa ser **subscrito** ao WABA (`POST /{waba-id}/subscribed_apps`) para receber webhooks.
- O número de teste do Meta (+1 555...) **não entrega mensagens para números brasileiros**.
- O template `hello_world` só funciona com números de teste. Com número real, usar mensagens de texto (requer janela de 24h aberta pelo usuário).
- A Meta normaliza números brasileiros removendo um dígito 9 — o número aparece como `8594132222` em vez de `85994132222`. O `ALLOWED_NUMBERS` deve incluir o formato que a Meta envia.
- **Cuidado com tabs** ao colar variáveis no Railway — um tab invisível no nome da variável causa `KeyError`.
- O `.dockerignore` é essencial para evitar que o `.env` local (com placeholders) sobreescreva variáveis do Railway dentro do container.
- O Dockerfile deve usar `${PORT:-8000}` em vez de porta fixa, pois o Railway define a porta via variável de ambiente.

## Status Atual

### O que foi feito
- [x] Conta no Meta Business criada
- [x] App "Gym" criado no Meta for Developers
- [x] WhatsApp Business Platform habilitada
- [x] Número real registrado e funcionando
- [x] Hello World funcionando (enviar "oi" → receber "Recebi sua mensagem: oi")
- [x] Servidor FastAPI com webhook no Railway
- [x] Webhook configurado na Meta (messages subscribed)
- [x] Filtro por número (ALLOWED_NUMBERS)
- [x] Transcrição de áudio implementada (Whisper API + ffmpeg)
- [x] Dockerfile + .dockerignore para deploy
- [x] App publicado (modo Live)
- [x] Deploy no Railway funcionando
- [x] Fluxo completo: mensagem real → webhook → resposta

### Próximos passos
1. Testar transcrição de áudio (enviar um áudio real)
2. Criar token permanente (System User) para substituir token temporário
3. Implementar Gym Companion (Fase 3)

## Custos Estimados (uso pessoal, 1-2 msgs/dia)

| Item | Custo/mês |
|---|---|
| WhatsApp API (service messages) | R$ 0 |
| OpenAI Whisper (transcrição) | ~R$ 1-5 |
| LLM (function calling) | ~R$ 1-5 |
| Railway (hosting) | R$ 0-25 (trial: $5 grátis) |
| **Total** | **~R$ 5-35** |

## Multi-usuário (futuro)

O projeto está sendo pensado desde o início para suportar múltiplos usuários:
- Dados sempre associados ao número do usuário
- Catálogos e preferências por usuário
- Allowlist de números autorizados
- Fluxo de OAuth por usuário para integrações Google
