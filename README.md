# Aisha — Assistente Pessoal via WhatsApp

Aisha é uma assistente pessoal inteligente que roda no WhatsApp Business API. Ela conversa, transcreve áudios, pesquisa na web, gera imagens, cria lembretes, analisa documentos, entende vídeos do YouTube e mantém contexto de conversa — tudo pelo WhatsApp.

## Funcionalidades

### Conversa com IA (roteamento automático de modelo)
- Qualquer mensagem de texto vai direto para o chat
- Um classificador leve (gpt-4.1-mini) decide qual modelo usar:
  - **Simples** (saudações, perguntas diretas, bate-papo casual) → `gpt-4.1` — rápido e barato
  - **Complexo** (raciocínio, pesquisa, geração de imagem, tarefas técnicas) → `gpt-5.4` — mais capaz
  - **Self** (perguntas sobre a própria Aisha, skills, como usar) → `gpt-4.1` com contexto de skills
- A Aisha responde de forma natural no idioma do usuário
- Mantém contexto da conversa por até 10 minutos de inatividade
- Para iniciar um novo assunto, diga: "nova conversa", "novo assunto", "mudar de assunto" ou "reset"

### Auto-Consciência
- A Aisha sabe responder sobre suas próprias capacidades
- Exemplos: "o que você faz?", "você pode criar lembretes?", "como funciona a transcrição?"
- O conteúdo das skills é carregado de `skills.md` (raiz do projeto) e injetado no prompt quando necessário

### Personalização e Perfil
- **Contexto pessoal:** envie informações sobre você e a Aisha lembra para sempre
- **Idioma:** peça para mudar o idioma da conversa ("vamos falar em inglês")
- **O que você sabe de mim?** A Aisha lista: contexto pessoal, lembretes ativos, preferências e estatísticas de uso
- Estatísticas rastreadas: áudios, imagens, documentos, vídeos YouTube, lembretes criados

### Transcrição de Áudio
- Áudios enviados **sem** mencionar "Aisha" são transcritos com Whisper e refinados com GPT-4o-mini
- O texto é devolvido limpo, sem vícios de linguagem ou hesitações

### Chat por Áudio
- Áudios que contêm a palavra **"Aisha"** são tratados como conversa
- Exemplos: "Aisha, qual a previsão do tempo?" ou "Aisha, me explica o que é inflação"
- O áudio é transcrito e o conteúdo é enviado para o modelo de chat

### Busca na Web
- Disponível automaticamente nas conversas
- O modelo decide quando usar com base no contexto
- Exemplo: "Aisha, quem ganhou o Oscar de melhor filme?"

### Geração de Imagem (gpt-image-1.5)
- Disponível automaticamente nas conversas
- O modelo decide quando usar com base no contexto
- Exemplo: "Aisha, gera uma imagem de um pôr do sol na praia"
- A imagem é enviada diretamente no WhatsApp

### Edição de Imagem
- Envie uma foto e a Aisha pergunta o que você quer fazer com ela
- Responda com texto ou áudio (não precisa dizer "Aisha" — ela já sabe que é sobre a imagem)
- Possibilidades: melhorar qualidade, mudar estilo, remover fundo, gerar variação, descrever, extrair texto, etc.
- A imagem é processada via Responses API com input multimodal (imagem + instrução) usando gpt-image-1.5
- Se a imagem for enviada com legenda, a legenda é usada como instrução diretamente
- Após receber o resultado, você pode pedir mais modificações na mesma conversa (edição iterativa via `previous_response_id`)
- Imagem pendente expira após 5 minutos sem instrução

### Documentos (PDF e Word)
- Envie um PDF ou DOCX e a Aisha resume automaticamente
- Para instruções específicas, envie o documento com legenda (ex: "extraia os valores")
- O contexto do documento é persistido na sessão — perguntas de follow-up funcionam
- Suporta documentos de até 20 MB

### Análise de Vídeos do YouTube (Gemini 2.5 Flash)
- Envie qualquer link do YouTube e a Aisha analisa o vídeo diretamente
- Pode enviar o link com instrução na mesma mensagem, ou só o link e a Aisha pergunta o que fazer
- Funciona com vídeos públicos de qualquer duração
- Exemplos de uso: resumo, transcrição, pontos principais, post para LinkedIn, perguntas sobre o conteúdo

### Leitura de Páginas Web (Jina Reader)
- Envie qualquer URL pública e a Aisha lê e processa o conteúdo
- Pode enviar o link com instrução na mesma mensagem, ou só o link e a Aisha pergunta o que fazer
- Funciona com artigos, notícias, blogs e documentações
- Exemplos de uso: resumo, tradução, extração de dados, explicação simplificada, post para LinkedIn

### Lembretes
- Criação via linguagem natural em português
- Aviso enviado por WhatsApp X minutos antes do evento (padrão: 15 min)
- Link gerado automaticamente para adicionar ao Google Calendar
- Suporte a lembretes recorrentes ("todo dia às 9h", "toda segunda às 7h")
- Gerenciamento completo: listar, cancelar e editar lembretes
- QA inteligente: se o horário já passou, sugere amanhã; se está muito próximo, pede confirmação

**Exemplos:**
```
"Aisha me lembra da reunião amanhã com João às 10h"
→ ✅ Lembrete criado! + link Google Calendar

"quais são meus lembretes?"
→ 📋 1. Reunião com João — 09/03 às 10:00

"cancela o lembrete 1"
→ ✅ Lembrete cancelado

"muda o lembrete 1 para as 11h"
→ ✅ Lembrete atualizado para 09/03 às 11:00
```

## Fluxo de Mensagens

```
Mensagem WhatsApp
        │
        ├── Texto ──► handle_chat (ver abaixo)
        │
        ├── Áudio ──► Whisper (transcrição)
        │                     │
        │                     ├── imagem pendente? ──► Processa imagem com instrução
        │                     ├── contém "Aisha" ───► Chat
        │                     └── sem "Aisha" ──────► Refinamento (GPT-4o-mini)
        │                                              └── devolve transcrição limpa
        │
        ├── Imagem ──┬── com legenda ──► Processa imagem com legenda como instrução
        │            └── sem legenda ──► Armazena imagem + pergunta o que fazer
        │
        └── Documento ──► Extrai texto + resume / responde instrução
                              └── contexto persistido para follow-ups

handle_chat (texto)
        │
        ├── 1. imagem pendente? ──► Processa imagem com instrução
        ├── 2. YouTube pendente? ──► Gemini 2.5 Flash ──► análise
        ├── 3. webpage pendente? ──► Jina Reader + gpt-4.1 ──► processa
        ├── 4. link YouTube? ──────► Gemini 2.5 Flash (ou armazena + pergunta)
        ├── 5. link web? ──────────► Jina Reader + gpt-4.1 (ou armazena + pergunta)
        ├── 6. classify (gpt-4.1-mini) ──► SELF? ──► gpt-4.1 + skills.md
        │                                   │        ├── set_context ──► salva contexto
        │                                   │        ├── set_language ──► muda idioma
        │                                   │        └── list_profile ──► lista perfil
        │                                   │
        │                                   └── SIMPLE/COMPLEX
        │                                         │
        ├── 7. menciona lembrete? ────────────────┤──► reminder
        │       ├── criar ──► Supabase + APScheduler + link GCal
        │       ├── listar ──► lista do Supabase
        │       ├── cancelar ──► remove do Supabase + APScheduler
        │       └── editar ──► atualiza Supabase + APScheduler
        │
        └── 8. conversa normal
                    ├── SIMPLE ──► gpt-4.1
                    └── COMPLEX ──► gpt-5.4 (web search, image gen)
```

## Memória de Sessão

A Aisha mantém contexto de conversa usando a Responses API da OpenAI com `previous_response_id`. O estado fica nos servidores da OpenAI (30 dias), e o Supabase guarda apenas o ID da última resposta por usuário.

| Situação | Comportamento |
|---|---|
| Dentro de 10 min de inatividade | Continua a conversa com contexto |
| Após 10 min sem mensagem | Nova sessão, sem contexto anterior |
| Usuário diz "nova conversa" | Reseta a sessão imediatamente |

## Arquitetura

```
whatsapp-agent/
├── aisha/                      # Pacote principal
│   ├── __init__.py
│   ├── app.py                  # FastAPI: webhook, roteamento, APScheduler lifespan
│   ├── config.py               # Variáveis de ambiente
│   ├── session.py              # Gerenciamento de sessões no Supabase (TTL 10min)
│   ├── user_profile.py         # CRUD de perfis de usuário (contexto, idioma, stats)
│   └── skills/                 # Habilidades da Aisha
│       ├── __init__.py
│       ├── chat.py             # Chat: classificador + gpt-4.1 + gpt-5.4 + auto-consciência
│       ├── reminder.py         # Lembretes: parsing LLM, agendamento, Google Calendar
│       ├── reminder_store.py   # CRUD Supabase para tabela reminders
│       ├── document.py         # Processamento de PDF/DOCX
│       ├── transcribe.py       # Transcrição de áudio via Whisper API + ffmpeg
│       ├── refine.py           # Refinamento de transcrições via GPT-4o-mini
│       ├── youtube.py          # Análise de vídeos YouTube via Gemini 2.5 Flash
│       ├── webpage.py          # Leitura de páginas web via Jina Reader
│       └── image_state.py      # Estado em memória para imagens pendentes (TTL 5min)
├── skills.md                   # Documentação das habilidades da Aisha
├── Dockerfile                  # Python 3.12 + ffmpeg
├── .dockerignore
├── .gitignore
├── .env                        # Variáveis locais (não vai pro deploy)
├── requirements.txt
├── README.md
└── logo.png
```

## Stack

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Framework | FastAPI + uvicorn |
| WhatsApp | Meta Cloud API (WhatsApp Business) |
| LLM classificador | OpenAI gpt-4.1-mini (detecta complexidade + self) |
| LLM chat simples | OpenAI gpt-4.1 via Responses API |
| LLM chat complexo | OpenAI gpt-5.4 via Responses API |
| LLM auto-consciência | OpenAI gpt-4.1 via Responses API + skills.md |
| LLM documentos | OpenAI gpt-4.1 via Responses API |
| LLM refinamento | OpenAI gpt-4o-mini |
| Transcrição | OpenAI Whisper (whisper-1) |
| Geração/edição de imagem | gpt-image-1.5 (via Responses API image_generation) |
| Busca na web | Ferramenta nativa da Responses API |
| Conversão de áudio | ffmpeg |
| Sessões | Supabase (PostgreSQL) |
| Perfis de usuário | Supabase (PostgreSQL) |
| Lembretes (agendamento) | APScheduler 4.x async + SQLAlchemy |
| Lembretes (parsing de datas) | dateparser (pt-BR nativo) |
| Análise de vídeos YouTube | Google Gemini 2.5 Flash |
| Leitura de páginas web | Jina Reader (r.jina.ai) |
| HTTP client | httpx (async) |
| Hosting | Railway (Docker) |

## Setup

### 1. Pré-requisitos

- Conta no [Meta for Developers](https://developers.facebook.com) com app WhatsApp configurado
- Número de telefone registrado na WhatsApp Business API
- Conta [OpenAI](https://platform.openai.com) com API key
- Projeto no [Supabase](https://supabase.com)

### 2. Banco de dados (Supabase)

No SQL Editor do Supabase, execute:

```sql
-- Tabela de sessões de conversa
CREATE TABLE sessions (
    phone TEXT PRIMARY KEY,
    response_id TEXT NOT NULL,
    last_active TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE sessions DISABLE ROW LEVEL SECURITY;

-- Tabela de lembretes
CREATE TABLE reminders (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone        TEXT NOT NULL,
    message      TEXT NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    timezone     TEXT NOT NULL DEFAULT 'America/Sao_Paulo',
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'sent', 'cancelled', 'failed')),
    is_recurring BOOLEAN NOT NULL DEFAULT FALSE,
    rrule        TEXT,
    job_id       TEXT UNIQUE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reminders_phone_status ON reminders (phone, status);
CREATE INDEX idx_reminders_scheduled    ON reminders (scheduled_at) WHERE status = 'pending';

ALTER TABLE reminders DISABLE ROW LEVEL SECURITY;

-- Tabela de perfis de usuário
CREATE TABLE user_profiles (
    phone            TEXT PRIMARY KEY,
    personal_context TEXT,
    language         TEXT DEFAULT 'pt-BR',
    stats            JSONB DEFAULT '{}'::jsonb,
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
```

### 3. Variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
WHATSAPP_TOKEN=seu_token_permanente
WHATSAPP_PHONE_ID=seu_phone_number_id
WEBHOOK_VERIFY_TOKEN=token_secreto_para_webhook
OPENAI_API_KEY=sk-...
ALLOWED_NUMBERS=5511999999999,5585999999999
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=sb_publishable_... ou sb_secret_...
DATABASE_PASSWORD=sua_senha_do_banco
USER_TIMEZONE=America/Sao_Paulo
REMINDER_LEAD_MINUTES=15
GEMINI_API_KEY=AIzaSy...
```

| Variável | Descrição |
|---|---|
| `WHATSAPP_TOKEN` | Token permanente da WhatsApp Cloud API (System User token) |
| `WHATSAPP_PHONE_ID` | Phone Number ID do número da Aisha |
| `WEBHOOK_VERIFY_TOKEN` | Token arbitrário para verificação do webhook pela Meta |
| `OPENAI_API_KEY` | Chave da API OpenAI |
| `ALLOWED_NUMBERS` | Números autorizados separados por vírgula (formato sem + e sem espaços) |
| `SUPABASE_URL` | URL do projeto Supabase (ex: `https://xxxxx.supabase.co`) |
| `SUPABASE_KEY` | Publishable ou Secret key do Supabase |
| `DATABASE_PASSWORD` | Senha do PostgreSQL (usada para conexão do APScheduler) |
| `USER_TIMEZONE` | Timezone do usuário para lembretes (padrão: `America/Sao_Paulo`) |
| `REMINDER_LEAD_MINUTES` | Minutos de antecedência para o aviso do lembrete (padrão: `15`) |
| `GEMINI_API_KEY` | API key do Google AI Studio para análise de vídeos YouTube (opcional) |
| `PORT` | Porta do servidor (Railway injeta automaticamente; padrão: 8000) |

### 4. Rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Instalar ffmpeg (macOS)
brew install ffmpeg

# Rodar o servidor
uvicorn aisha.app:app --reload --port 8000
```

Para expor o servidor local ao webhook da Meta, use [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

Configure a URL gerada (`https://xxxx.ngrok.io/webhook`) no painel da Meta.

### 5. Deploy no Railway

1. Conecte o repositório no [Railway](https://railway.app)
2. O Railway detecta o `Dockerfile` automaticamente
3. Configure todas as variáveis de ambiente no painel do Railway (Settings → Variables)
4. A URL de produção será algo como: `https://seu-projeto.up.railway.app`
5. Configure essa URL como webhook no Meta for Developers

### 6. Configurar webhook na Meta

No painel de developers.facebook.com:
- URL do webhook: `https://seu-dominio/webhook`
- Verify token: o valor de `WEBHOOK_VERIFY_TOKEN`
- Subscription fields: `messages`

## Configuração Meta Business

| Item | Valor |
|---|---|
| App | Gym (developers.facebook.com) |
| Número da Aisha | +55 85 9413-2222 |
| Phone Number ID | `1018015604729721` |
| WhatsApp Business Account ID | `1265667928785504` |

### Como gerar o token permanente

1. Acesse [business.facebook.com](https://business.facebook.com) → Settings → System Users
2. Crie um System User com role Admin
3. Clique em **Generate token** → selecione o app → marque `whatsapp_business_management` e `whatsapp_business_messaging`
4. Copie o token gerado (não expira)

## Custos Estimados (uso pessoal)

| Serviço | Custo |
|---|---|
| WhatsApp Cloud API (service messages) | Gratuito |
| OpenAI Whisper (transcrição de áudio) | ~$0.006/min |
| OpenAI gpt-4.1-mini (classificador de complexidade) | ~$0.00001/msg |
| OpenAI gpt-4.1 (chat simples + self + docs) | ~$0.001/msg |
| OpenAI gpt-5.4 (chat complexo) | ~$0.005-0.015/msg |
| OpenAI GPT-4o-mini (refinamento de transcrição) | ~$0.001/msg |
| OpenAI gpt-image-1.5 (imagem) | ~$0.02-0.08/imagem |
| OpenAI web_search (busca) | ~$0.001/chamada |
| Jina Reader (páginas web) | Gratuito |
| Supabase | Gratuito (free tier) |
| Railway | $0-25/mês (trial: $5 créditos grátis) |

## Notas de implementação

- **Deduplicação:** A Meta pode enviar o mesmo webhook duas vezes. O app mantém um cache de até 1000 IDs de mensagens processadas para evitar respostas duplicadas.
- **Allowlist:** Apenas números em `ALLOWED_NUMBERS` recebem respostas. Números brasileiros chegam sem o 9 extra (ex: `5585941322222` → `558594132222`).
- **ffmpeg:** Necessário para converter áudio OGG/Opus do WhatsApp para MP3 antes de enviar ao Whisper. Está incluído no Dockerfile.
- **Chunking de áudio:** Áudios maiores que 24 MB são divididos em chunks de 10 minutos e transcritos em paralelo (até 4 workers).
- **`.dockerignore`:** Impede que o `.env` local (com placeholders) sobreescreva as variáveis de produção dentro do container.
- **Porta dinâmica:** O Dockerfile usa `${PORT:-8000}` para compatibilidade com Railway, que injeta a porta via variável de ambiente.
- **Números brasileiros:** A Meta normaliza números BR removendo um dígito 9. Configure `ALLOWED_NUMBERS` com o formato que a Meta envia.
- **Timezone:** O servidor roda em UTC (Railway). Lembretes usam `USER_TIMEZONE` para calcular horários relativos corretamente.
- **PgBouncer:** O Supabase usa PgBouncer em modo transaction, que não suporta prepared statements. O engine é criado com `statement_cache_size=0` para evitar `DuplicatePreparedStatementError` na inicialização do APScheduler.
- **Logs:** Se a pasta `logs/` existir na raiz do projeto, o app escreve em `logs/aisha.log` com rotação automática (5 MB × 3 arquivos). Caso contrário, só imprime no stdout.
