# Aisha — Assistente Pessoal via WhatsApp

Aisha é uma assistente pessoal orientada a tarefas que roda no WhatsApp Business API. Ela não é um chatbot para bate-papo — seu papel é executar ações concretas: transcrever áudios, pesquisar na web, gerar imagens, criar lembretes, agendar tarefas recorrentes, analisar documentos e vídeos do YouTube, e montar mapas com raio — tudo pelo WhatsApp.

## Missão e princípios

**Missão:** tirar tarefas da cabeça do usuário com o mínimo de fricção, dentro do app que ele já usa todos os dias.

**Visão:** uma assistente que não espera ser perguntada — ela lembra, monitora e entrega antes que você precise pedir.

**Princípios:**
1. Ação > conversa. Cada interação termina em algo feito ou uma pergunta objetiva.
2. WhatsApp é a interface inteira. Nenhum app, login ou dashboard novo.
3. Ambiguidade gera pergunta, nunca suposição. Limite gera honestidade ("não tenho essa habilidade"), nunca invenção.
4. Proatividade agendada: o valor máximo da Aisha é quando ela inicia a conversa.
5. Memória a serviço do usuário: ela lembra para personalizar, e o usuário sempre pode ver e apagar o que ela sabe.

**Não-objetivos (por enquanto):** companheira emocional/roleplay, terapia, atendimento comercial para empresas, chamadas de voz, grupos.

**Filtro para novas skills** — se falhar em uma, não entra:
1. Resolve uma tarefa recorrente real do usuário-alvo?
2. Funciona bem no formato mensagem (texto/áudio/mídia)?
3. Executa em segundos ou é agendável?
4. É melhor aqui do que seria abrindo o ChatGPT? (se não usa proatividade, memória ou o contexto do WhatsApp, provavelmente não)

**Voz:** direta, sem alongar conversa. Emojis só funcionais (✅ 📋 ⏳). Idioma do usuário.

**Estágio do produto:** hoje pessoal, com allowlist. Aberto ao público quando existirem sistema de usuários, rate limiting e billing.

## Roadmap

| Estágio | Foco |
|---|---|
| Agora | Produto pessoal / beta fechado. Agente único com tools, memória de longo prazo, webhook confiável. |
| Em seguida | Observabilidade (Langfuse, se aprovado), evals de regressão, pending states 100% no banco. |
| Depois | Multi-usuário + rate limiting + billing para abertura pública. Sem datas. |

## Funcionalidades

### Comportamento orientado a tarefas
- **Ação clara** (criar lembrete, pesquisar, resumir, gerar imagem) → executa diretamente
- **Pergunta direta** ("qual o dólar hoje?", "o que é inflação?") → responde com informação
- **Conteúdo ambíguo** (texto encaminhado, ata, link sem instrução) → pergunta: "O que você quer que eu faça com isso?"
- **Pedido impossível** → responde: "Não tenho essa habilidade."
- Responde de forma natural no idioma do usuário
- Mantém contexto da conversa por até 10 minutos de inatividade
- Para iniciar um novo assunto, diga: "nova conversa", "novo assunto", "mudar de assunto" ou "reset"
- Feedback imediato: marca a mensagem como lida e mostra "digitando..." assim que o webhook chega; em seguida envia "⏳ Processando..." em paralelo com a hidratação de estado, antes do agente
- Se o usuário enviar outra mensagem enquanto a anterior ainda está sendo processada, a Aisha avisa que está ocupada e pede para aguardar

### Personalização e Perfil
- **Contexto pessoal:** envie informações sobre você e a Aisha lembra para sempre
- **Idioma:** peça para mudar o idioma da conversa ("vamos falar em inglês")
- **O que você sabe de mim?** A Aisha lista: contexto pessoal, lembretes ativos, tarefas agendadas, preferências e estatísticas de uso
- Estatísticas rastreadas: áudios, imagens, documentos, vídeos YouTube, lembretes criados, tarefas agendadas criadas

### Transcrição de Áudio
- Áudios transcritos com Whisper e refinados com Gemini 2.5 Flash (fallback: Gemini 2.0 Flash Lite)
- O texto é devolvido limpo, sem vícios de linguagem ou hesitações
- **Roteamento inteligente por contexto de sessão:**
  - **Nova sessão + sem "Aisha"** → infere que a pessoa quer transcrever (ex: encaminhar áudio para alguém)
  - **Sessão ativa + sem "Aisha"** → trata como instrução de voz para o chat
  - **"Aisha, transcreva..."** → sempre transcreve, independente do contexto
- **Correção retroativa:** se a Aisha respondeu quando a pessoa queria só a transcrição, basta dizer "eu só queria a transcrição" e ela refina o áudio original (guardado por 5 minutos)

### Chat por Áudio
- Áudios que contêm a palavra **"Aisha"** em sessão ativa são tratados como conversa
- Exemplos: "Aisha, qual a previsão do tempo?" ou "Aisha, me explica o que é inflação"
- O áudio é transcrito e o conteúdo é enviado para o modelo de chat

### Busca na Web
- Disponível automaticamente nas conversas
- O modelo decide quando usar com base no contexto
- Exemplo: "Aisha, quem ganhou o Oscar de melhor filme?"

### O que estão falando no X (Twitter)
- Consulta posts públicos via xAI Grok (`x_search`) — não é scraping
- Use quando quiser o que pessoas estão postando, não só notícias da web
- Exemplos: "o que estão falando no X sobre o Pix?", "qual o clima no Twitter sobre a Copa?"
- Combina com tarefa agendada: briefing diário do que o X está dizendo sobre um assunto
- Requer `XAI_API_KEY`

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
- Suporta documentos de até 50 MB
- **PDFs escaneados (imagem):** detectados automaticamente e processados via OCR com visão do modelo (gpt-4.1), sem perda de conteúdo
- **PDFs nativos (texto):** extração direta via pymupdf4llm, sem custo de visão
- **DOCX:** extrai parágrafos e tabelas preservando a estrutura do documento

### Análise de Vídeos do YouTube (Gemini 2.5 Flash)
- Envie qualquer link do YouTube e a Aisha analisa o vídeo diretamente
- Pode enviar o link com instrução na mesma mensagem, ou só o link e a Aisha pergunta o que fazer
- Vídeos curtos (menos de 25 min e ≤ 80 MB) são analisados direto pelo Gemini
- Vídeos longos (≥ 25 min, ou > 80 MB) — ou pedido explícito de TXT: resumo no chat + transcrição completa em TXT para download
- Exemplos de uso: resumo, transcrição, pontos principais, post para LinkedIn, perguntas sobre o conteúdo

### Leitura de Páginas Web (Jina Reader)
- Envie qualquer URL pública e a Aisha lê e processa o conteúdo
- Pode enviar o link com instrução na mesma mensagem, ou só o link e a Aisha pergunta o que fazer
- Funciona com artigos, notícias, blogs e documentações
- Exemplos de uso: resumo, tradução, extração de dados, explicação simplificada, post para LinkedIn

### Mapa com raio (círculo em torno de um ponto)
- Informe um endereço e um raio; a Aisha envia um mapa Google (visual CalcMaps) com círculo azul e pino vermelho
- Unidades: metros, km (padrão se você só mandar o número) ou milhas; faixa de 50 m a 50 km
- Se o endereço for ambíguo, ela lista as opções. Follow-up ("agora com 5 km") reusa o último ponto
- Não usa geração de imagem por IA — geocodifica no Nominatim e pede o PNG à Google Maps Static API
- Requer `GOOGLE_MAPS_API_KEY`
- Exemplos: "mapa de 2 km em torno da Av. Beira Mar 123, Fortaleza"

### Lembretes
- Criação via linguagem natural em português
- Aviso enviado por WhatsApp X minutos antes do evento (padrão: 15 min)
- Link gerado automaticamente para adicionar ao Google Calendar
- Suporte a lembretes recorrentes ("todo dia às 9h", "toda segunda às 7h")
- Gerenciamento completo: listar, cancelar e editar lembretes
- QA inteligente: se o horário já passou, sugere amanhã; se está muito próximo, pede confirmação
- **Anti-duplicata:** o agente vê os lembretes ativos no system prompt e usa `edit_reminder` ao invés de criar novos quando o follow-up é sobre o mesmo evento

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

### Tarefas Agendadas (Scheduled Tasks)
- Diferente dos lembretes (que enviam texto fixo), as tarefas agendadas **executam uma ação do agente** a cada disparo
- Cada execução usa `gpt-5.4` com busca na web para informações atualizadas
- Suporte a agendamento via cron: diário, semanal, mensal, dias específicos
- Gerenciamento completo: criar, listar e cancelar tarefas
- Jobs persistem no banco e são restaurados automaticamente no startup do servidor

**Exemplos:**
```
"toda segunda me mande um relatório com as últimas notícias sobre o Irã"
→ ✅ Tarefa agendada criada! (cron: toda segunda às 09:00)

"todo dia às 7h me mande o resumo do mercado financeiro"
→ ✅ Tarefa agendada criada! (cron: todo dia às 07:00)

"quais são minhas tarefas agendadas?"
→ 📋 1. Relatório Irã — 0 9 * * 1

"cancela a tarefa agendada 1"
→ ✅ Tarefa agendada cancelada
```

## Fluxo de Mensagens

```
Mensagem WhatsApp
        │
        ├── Texto ──► handle_chat (ver abaixo)
        │
        ├── Áudio ──► Whisper (transcrição)
        │                     │
        │                     ├── imagem pendente? ──────────────────► Processa imagem com instrução
        │                     ├── "Aisha, transcreva ..." ───────────► Refinamento (Gemini 2.5 Flash)
        │                     ├── nova sessão + sem "Aisha" ─────────► Refinamento (Gemini 2.5 Flash)
        │                     └── sessão ativa (com ou sem "Aisha") ─► Chat
        │                                    └── transcrição bruta guardada 5min p/ correção retroativa
        │
        ├── Imagem ──┬── com legenda ──► Processa imagem com legenda como instrução
        │            └── sem legenda ──► Armazena imagem + pergunta o que fazer
        │
        └── Documento ──► Detecta tipo
                              ├── PDF nativo ──► pymupdf4llm ──► gpt-4.1 resume/responde
                              ├── PDF escaneado ──► visão gpt-4.1 (OCR) ──► gpt-4.1 resume/responde
                              └── DOCX ──► python-docx (parágrafos + tabelas) ──► gpt-4.1 resume/responde
                              └── contexto persistido para follow-ups

handle_chat (texto)
        │
        ├── 0. pedido retroativo de transcrição? ──► refina transcrição bruta (5min TTL)
        ├── 1. estado pendente? ──► CONTINUE / CANCEL / NEW_INTENT
        ├── 2. saudação trivial? ──► gpt-5.6-luna (Fast mode, sem tools)
        └── 3. agente (gpt-5.6-sol, Fast mode)
                    └── loop de tools (até 10 iterações, em paralelo)
                          ├── web_search / search_x / image_generation / draw_radius_map
                          ├── lembretes e tarefas agendadas
                          ├── YouTube / webpage / download
                          └── memória (save / search / list / forget)
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
│   ├── app.py                  # FastAPI: webhook assíncrono, APScheduler lifespan
│   ├── agent.py                # Agentic loop (gpt-5.6-sol) + fast-path (luna), ambos em Fast mode
│   ├── models.py               # IDs canônicos dos modelos
│   ├── routing.py              # Helpers puros de roteamento (testáveis)
│   ├── config.py               # Variáveis de ambiente
│   ├── supabase_http.py        # Cliente HTTP compartilhado para o Supabase
│   ├── session.py              # Sessões no Supabase (TTL 10min)
│   ├── user_profile.py         # Perfis (contexto, idioma, stats)
│   ├── tools/                  # Wrappers de tools do agente
│   └── skills/                 # Habilidades (lembrete, doc, youtube, memória…)
├── skills.md                   # Guia de habilidades (alinhado à missão)
├── tests/                      # Testes das partes puras
├── Dockerfile
├── requirements.txt
└── README.md
```

## Stack

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Framework | FastAPI + uvicorn |
| WhatsApp | Meta Cloud API (WhatsApp Business) |
| LLM agente | OpenAI gpt-5.6-sol via Responses API, Fast mode |
| LLM fast-path | OpenAI gpt-5.6-luna, Fast mode |
| LLM extração / documentos / OCR | OpenAI gpt-5.6-sol, Fast mode |
| LLM refinamento | Google Gemini 3.6 Flash (fallback: 2.5 Flash) |
| Transcrição | OpenAI Whisper (whisper-1) |
| Geração/edição de imagem | image_generation (Responses API) |
| Mapa com raio | Nominatim + Google Maps Static API (`draw_radius_map`) |
| Busca na web | Ferramenta nativa da Responses API |
| Busca no X (Twitter) | xAI Grok `x_search` via tool `search_x` |
| Memória de longo prazo | Embeddings text-embedding-3-small + tabela memories |
| Conversão de áudio | ffmpeg |
| Sessões / perfis / lembretes | Supabase (PostgreSQL) |
| Lembretes (agendamento) | APScheduler 4.x async + SQLAlchemy |
| Tarefas agendadas (execução) | APScheduler CronTrigger + agente (web_search e/ou search_x) |
| Análise de vídeos YouTube | Google Gemini 3.6 Flash (fallback: 2.5 Flash) |
| Leitura de páginas web | Jina Reader (r.jina.ai) |
| HTTP client | httpx (async) |
| Hosting | Railway (Docker) |

## Setup

### 1. Pré-requisitos

- Conta no [Meta for Developers](https://developers.facebook.com) com app WhatsApp configurado
- Número de telefone registrado na WhatsApp Business API
- Conta [OpenAI](https://platform.openai.com) com API key
- Conta [xAI](https://console.x.ai) com API key (opcional — busca no X/Twitter)
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
    timezone         TEXT,
    stats            JSONB DEFAULT '{}'::jsonb,
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;

-- Migração: adicionar coluna timezone (executar se a tabela já existir)
-- ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS timezone TEXT;

-- Tabela de tarefas agendadas
CREATE TABLE scheduled_tasks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone            TEXT NOT NULL,
    name             TEXT NOT NULL,
    prompt           TEXT NOT NULL,
    cron_expression  TEXT NOT NULL,
    timezone         TEXT NOT NULL DEFAULT 'America/Sao_Paulo',
    job_id           TEXT,
    active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_scheduled_tasks_phone_active ON scheduled_tasks (phone, active);

ALTER TABLE scheduled_tasks DISABLE ROW LEVEL SECURITY;
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_memories_phone ON memories (phone);
ALTER TABLE memories DISABLE ROW LEVEL SECURITY;
CREATE TABLE pending_states (
    phone TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    blob_b64 TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (phone, kind)
);
CREATE INDEX idx_pending_states_phone_expires ON pending_states (phone, expires_at);
ALTER TABLE pending_states DISABLE ROW LEVEL SECURITY;
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
XAI_API_KEY=xai-...
GOOGLE_MAPS_API_KEY=AIzaSy...
WHATSAPP_APP_SECRET=app_secret_da_meta
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
| `XAI_API_KEY` | API key da xAI (console.x.ai) para buscar o que pessoas estão falando no X (opcional) |
| `GOOGLE_MAPS_API_KEY` | Chave da Google Maps Static API para mapa com raio (opcional; sem ela a skill recusa) |
| `WHATSAPP_APP_SECRET` | App Secret da Meta para validar `X-Hub-Signature-256`. Se vazio, a verificação é pulada. |
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

### 6. Logs, variáveis e banco (MCP)

A forma recomendada de operar produção a partir do Cursor é via **MCP** (Model Context Protocol). O agente chama tools estruturadas em linguagem natural — sem montar queries GraphQL ou lembrar comandos do CLI.

A config do projeto fica em `.cursor/mcp.json`. Essa pasta é convenção **do Cursor** (assim como o VS Code usa `.vscode/`). Não é exigência do protocolo MCP em si; outros editores usam caminhos diferentes. Versionamos `.cursor/mcp.json` no repo para que qualquer dev abra o projeto já com Railway + Supabase configurados.

**Pré-requisitos (uma vez):**
```bash
npm install -g @railway/cli
railway login        # abre o browser para autenticar
railway link         # Aisha-agent → production
```

Depois, recarregue o Cursor (ou abra **Settings → MCP**) para carregar os servidores.

**Servidores configurados:**

| MCP | O que faz | Exemplos no chat |
|---|---|---|
| **Railway** (local) | Logs, variáveis de ambiente, deploy | *"Mostra erros recentes do whatsapp-agent"*, *"Atualiza WHATSAPP_TOKEN no Railway"* |
| **Supabase** (remoto, read-only) | Consultas SQL no banco de produção | *"Lista lembretes pendentes do 558599065040"*, *"Quantas sessões ativas existem?"* |

O Supabase MCP usa `read_only=true` por padrão — só consulta, não altera dados.

**Autenticação:**
- **Railway:** usa o CLI já logado (`railway login`). Se expirar, rode `railway login` de novo.
- **Supabase:** OAuth no browser na primeira conexão (sem PAT no disco).

**Fallback via CLI** (quando MCP não estiver disponível):
```bash
railway logs --service whatsapp-agent
railway variables --service whatsapp-agent
railway variables --service whatsapp-agent --set "NOME=valor"
```

> **Observação:** O `service` no config local fica `null` após o `railway link` — passe sempre `--service whatsapp-agent` no CLI.

### 7. Configurar webhook na Meta

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
| OpenAI gpt-5.6-luna (fast-path, Fast mode) | Premium sobre o preço padrão por token |
| OpenAI gpt-5.6-sol (agente + extração + docs + OCR, Fast mode) | Premium sobre o preço padrão por token |
| Google Gemini 3.6 Flash (refinamento / YouTube) | ~$0.001/msg |
| OpenAI gpt-image-1.5 (imagem) | ~$0.02-0.08/imagem |
| OpenAI web_search (busca) | ~$0.001/chamada |
| xAI x_search (posts do X) | ~$0.005/chamada + tokens Grok |
| OpenAI gpt-5.6-sol (tarefa agendada com web search, Fast mode) | Premium sobre o preço padrão por token |
| OpenAI embeddings (memória) | ~$0.00002/fato |
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
- **Tarefas agendadas vs. lembretes:** Lembretes enviam texto fixo na hora agendada. Tarefas agendadas executam o agente (web e/ou X) a cada disparo, gerando conteúdo dinâmico. Ambos usam APScheduler com persistência no PostgreSQL.
- **Webhook assíncrono:** o POST `/webhook` valida a assinatura e devolve 200 imediatamente; o processamento roda em background para a Meta não reenviar por timeout. A primeira reação visível é o indicador de "digitando..." (mark-as-read + typing), disparado antes de hidratar estado ou chamar o LLM.
- **GET `/health`:** probe de liveness. Útil como keep-alive no Railway para evitar cold start de ~20-30s na primeira mensagem do dia.
- **Memória:** fatos duradouros vão para a tabela `memories` (embedding + busca por similaridade). O usuário pode listar e apagar.
- **Restauração de jobs:** No startup, o servidor começa a aceitar webhooks assim que o APScheduler sobe; a restauração das tarefas agendadas roda em background para não atrasar a primeira mensagem após um deploy/cold start.
- **Logs:** Se a pasta `logs/` existir na raiz do projeto, o app escreve em `logs/aisha.log` com rotação automática (5 MB × 3 arquivos). Caso contrário, só imprime no stdout.
- **Anti-duplicata de lembretes:** A cada chamada ao agente, os lembretes ativos do usuário são buscados no Supabase e injetados no `instructions` do modelo. Isso permite que o modelo use `edit_reminder` em follow-ups (ex: "inclua o endereço no lembrete") ao invés de criar um segundo lembrete sobre o mesmo evento.
