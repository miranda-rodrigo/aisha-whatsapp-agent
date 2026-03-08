# Aisha — Assistente Pessoal via WhatsApp

Aisha é uma assistente pessoal inteligente que roda no WhatsApp Business API. Ela conversa, transcreve áudios, pesquisa na web, gera imagens e mantém contexto de conversa — tudo pelo WhatsApp.

## Funcionalidades

### Conversa com IA (GPT-5.4)
- Qualquer mensagem de texto vai direto para o modelo
- A Aisha responde de forma natural no idioma do usuário
- Mantém contexto da conversa por até 10 minutos de inatividade
- Para iniciar um novo assunto, diga: "nova conversa", "novo assunto", "mudar de assunto" ou "reset"

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

## Fluxo de Mensagens

```
Mensagem WhatsApp
        │
        ├── Texto ──────────────────────────────► Chat (GPT-5.4)
        │
        └── Áudio ──► Whisper (transcrição)
                              │
                              ├── contém "Aisha" ──► Chat (GPT-5.4)
                              │
                              └── sem "Aisha" ────► Refinamento (GPT-4o-mini)
                                                     └── devolve transcrição

Chat (GPT-5.4)
        │
        ├── usa web_search ──► resposta com info atualizada
        ├── usa image_generation ──► envia imagem no WhatsApp
        └── resposta direta ──► envia texto
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
├── app.py          # FastAPI: webhook, roteamento de mensagens, envio de respostas
├── chat.py         # Skill de conversa via Responses API (GPT-5.4)
├── session.py      # Gerenciamento de sessões no Supabase
├── transcribe.py   # Transcrição de áudio via Whisper API + ffmpeg
├── refine.py       # Refinamento de transcrições via GPT-4o-mini
├── config.py       # Variáveis de ambiente
├── Dockerfile      # Python 3.12 + ffmpeg
├── requirements.txt
└── .env            # Variáveis locais (não vai pro deploy)
```

## Stack

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Framework | FastAPI + uvicorn |
| WhatsApp | Meta Cloud API (WhatsApp Business) |
| LLM (chat) | OpenAI GPT-5.4 via Responses API |
| LLM (refinamento) | OpenAI GPT-4o-mini |
| Transcrição | OpenAI Whisper (whisper-1) |
| Geração de imagem | gpt-image-1.5 |
| Busca na web | Ferramenta nativa da Responses API |
| Conversão de áudio | ffmpeg |
| Sessões | Supabase (PostgreSQL) |
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
CREATE TABLE sessions (
    phone TEXT PRIMARY KEY,
    response_id TEXT NOT NULL,
    last_active TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE sessions DISABLE ROW LEVEL SECURITY;
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
| `PORT` | Porta do servidor (Railway injeta automaticamente; padrão: 8000) |

### 4. Rodar localmente

```bash
# Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Instalar ffmpeg (macOS)
brew install ffmpeg

# Rodar o servidor
uvicorn app:app --reload --port 8000
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
| OpenAI GPT-4o-mini (refinamento) | ~$0.001/msg |
| OpenAI GPT-5.4 (chat) | ~$0.003-0.015/msg |
| OpenAI gpt-image-1.5 (imagem) | ~$0.02-0.08/imagem |
| OpenAI web_search (busca) | ~$0.001/chamada |
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
