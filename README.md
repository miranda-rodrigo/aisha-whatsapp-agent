# WhatsApp Personal Agent

Agente pessoal via WhatsApp com skills modulares.

## Visão Geral

Um agente que roda no WhatsApp Business API (Meta Cloud API) e responde apenas a mensagens do meu número. Funciona como um assistente pessoal com skills que podem ser adicionadas incrementalmente.

## Skills Planejadas

### Fase 1 — Hello World
- Receber e responder mensagens de texto simples via WhatsApp
- Filtro por número (só responde ao meu)

### Fase 2 — Transcrição de Áudio
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
- **Railway** — hosting (Docker)
- **httpx** — HTTP client async

## Setup — Meta Business Platform

### Conta criada
- **Meta Business Portfolio:** Price Pulse (consultoria com CNPJ ativo)
- **App:** numeroclaro (developers.facebook.com)
- **Use case:** Connect with customers through WhatsApp

### Credenciais (número real)
- **Número do agente:** +55 85 99413-2222
- **Phone Number ID:** `1018015604729721`
- **WhatsApp Business Account ID:** `1265667928785504`
- **Access Token:** temporário, 24h (gerar em developers.facebook.com → API Setup → Generate access token)

### Notas de setup
- O número precou ser registrado manualmente via API (`POST /{phone-number-id}/register`) após ser adicionado no painel — a UI do Meta não faz isso automaticamente.
- O número de teste do Meta (+1 555 159 1021) **não entrega mensagens para números brasileiros** — limitação conhecida. Por isso usamos um número real desde o início.
- O template `hello_world` só funciona com números de teste. Com número real, usar mensagens de texto (requer janela de 24h aberta pelo usuário).

## Status Atual

### O que foi feito
- [x] Conta no Meta Business criada
- [x] App criado no Meta for Developers
- [x] WhatsApp Business Platform habilitada
- [x] Número real (+55 85 99413-2222) registrado e funcionando
- [x] Hello World funcionando (enviar "oi" → receber resposta via API)
- [x] Servidor FastAPI com webhook (recebe mensagens automaticamente)
- [x] Filtro por número (ALLOWED_NUMBERS)
- [x] Transcrição de áudio (Whisper API + ffmpeg)
- [x] Dockerfile para deploy no Railway

### Próximos passos
1. Criar System User token permanente no Meta Business Manager
2. Deploy no Railway
3. Configurar webhook no Meta apontando para URL do Railway
4. Testar fluxo completo: áudio → transcrição

## Custos Estimados (uso pessoal, 1-2 msgs/dia)

| Item | Custo/mês |
|---|---|
| WhatsApp API (service messages) | R$ 0 |
| OpenAI Whisper (transcrição) | ~R$ 1-5 |
| LLM (function calling) | ~R$ 1-5 |
| Servidor (VPS/serverless) | R$ 0-30 |
| **Total** | **~R$ 5-40** |

## Multi-usuário (futuro)

O projeto está sendo pensado desde o início para suportar múltiplos usuários:
- Dados sempre associados ao número do usuário
- Catálogos e preferências por usuário
- Allowlist de números autorizados
- Fluxo de OAuth por usuário para integrações Google
