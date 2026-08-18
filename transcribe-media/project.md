# Transcribe Media

Skill de transcrição para Cursor, Claude Code e Cloud Agent. Não é uma feature da Aisha no WhatsApp. É um projeto separado: uma pasta com `SKILL.md` + tools, não um único markdown.

## Objetivo

O usuário aponta qualquer fonte que tenha fala (arquivo local, URL, anexo da conversa) e recebe uma transcrição fiel. Depois da transcrição bruta, a skill **sempre pergunta** o que ele quer fazer com o texto — nunca decide sozinha se entrega o bruto, o melhorado ou outra variante.

A saída é sempre **as duas coisas**: o texto no chat e um arquivo no disco.

## Princípios

1. Bruto primeiro. A transcrição Whisper/legendas é a fonte da verdade. Melhoria só acontece se o usuário pedir.
2. Perguntar depois de transcrever. Não perguntar antes o formato se isso atrasar o trabalho; transcreve, mostra uma prévia do bruto, e oferece as opções.
3. Arquivo + texto. Chat sem arquivo some. Arquivo sem texto no chat obriga o usuário a abrir o disco. Os dois.
4. Tools separadas. Cada passo (extrair áudio, transcrever, limpar, melhorar, gravar) é uma tool. A skill orquestra; não mistura tudo num script só.
5. Sem instalar nada sem perguntar. Se faltar `ffmpeg`, `yt-dlp` ou o pacote `openai`, a skill para e pergunta.
6. Uma chave: `OPENAI_API_KEY`. Whisper e melhoria com IA usam a mesma chave.

## Entradas

Qualquer coisa que possa carregar fala. Se não der para extrair áudio nem texto, a skill diz o limite com honestidade.

**Arquivos de vídeo:** `.mp4`, `.webm`, `.mkv`, `.mov`, `.avi`, e o que o `ffmpeg` abrir.

**Arquivos de áudio:** `.mp3`, `.m4a`, `.wav`, `.ogg`, `.opus`, `.webm`, `.aac`, `.flac`.

**Arquivos de texto já transcritos:** `.txt`, `.srt`, `.vtt`. Nesse caso pula Whisper e trata o conteúdo como bruto.

**URLs:** YouTube, X/Twitter, e qualquer link que o `yt-dlp` resolva. Primeiro tenta legendas; se não houver, baixa só o áudio e manda para o Whisper.

**Outros:** o usuário pode mandar “qualquer coisa” — um vídeo do celular, um opus do WhatsApp, um recorte do X, um mp3 de podcast. Se o arquivo tiver faixa de áudio, transcreve. Se for imagem, PDF sem áudio, ou arquivo corrompido: “Não consigo transcrever isso.”

## Fluxo

```
fonte (arquivo | URL | texto)
        │
        ▼
  detectar tipo
        │
        ├── vídeo/áudio ──► extract_audio ──► transcribe_audio (Whisper)
        ├── URL ──────────► fetch_captions ──► se vazio: extract_audio + Whisper
        └── .txt/.srt/.vtt ► normalize_text
        │
        ▼
  gravar sempre raw.txt (+ raw.srt se houver timestamps)
        │
        ▼
  mostrar prévia do BRUTO no chat + caminho do arquivo
        │
        ▼
  PERGUNTAR o que o usuário quer agora
        │
        ├── bruto (já está pronto)
        ├── melhorado com IA
        ├── limpo sem IA
        ├── outro idioma
        ├── timestamps / SRT / VTT
        ├── resumo junto
        └── as duas versões (bruto e melhorado)
        │
        ▼
  entregar texto no chat + arquivo(s) correspondente(s)
```

A pergunta depois da transcrição é obrigatória, mesmo se o usuário já tiver dito “transcreve e melhora” na primeira mensagem. Se a intenção já veio clara (“quero o bruto em inglês, arquivo .srt”), executa direto e não pergunta de novo. Ambiguidade gera pergunta; intenção clara executa.

## Opções (sempre oferecer)

Depois da prévia do bruto, a skill lista as opções. O usuário pode combinar.

| Opção | O que acontece |
|---|---|
| **Bruta** | Entrega `raw.txt` como está. Padrão se ele só confirmar “bruta”. |
| **Melhorada (com IA)** | LLM edita o bruto: tira vícios, hesitações, autocorreções; preserva idioma, tom e extensão. Grava `improved.txt`. Não resume. |
| **Limpa (sem IA)** | Limpeza determinística: espaços, pontuação grudada, pausas óbvias (`uh`, `um`, `hã`, `hmm`). Não apaga palavras reais (`tipo`, `né`, `então`). Grava `cleaned.txt`. |
| **Idioma do arquivo** | O usuário diz em que língua quer o arquivo. Ver seção abaixo. |
| **Com timestamps** | Além do `.txt`, gera `.srt` e/ou `.vtt`. |
| **Resumo** | Um resumo curto **além** da transcrição, nunca no lugar dela. |
| **As duas** | Bruto e melhorado, dois arquivos, os dois textos (ou bruto no arquivo e melhorado no chat, se o texto for longo demais). |
| **Só o arquivo** / **só o chat** | Exceção explícita. O padrão continua sendo os dois. |

A skill pode sugerir mais de uma opção na mesma pergunta, por exemplo:

> Transcrição bruta pronta (12 min, pt-BR). Prévia: “…”
> Arquivo: `transcripts/entrevista-joao/raw.txt`
>
> Quer a versão bruta, melhorada com IA, limpa sem IA, em outro idioma, com timestamps, ou um resumo junto?

## Idioma

O usuário pode pedir o idioma da transcrição a qualquer momento — na primeira mensagem ou depois da pergunta.

- **Não pediu idioma:** Whisper/legendas no idioma original da fala. O arquivo sai nesse idioma.
- **Pediu idioma igual ao da fala:** transcreve nessa língua (Whisper com `language=` quando der para inferir).
- **Pediu idioma diferente:** transcreve no original (bruto permanece fiel) e a versão entregue no idioma pedido é uma **tradução** da transcrição, em arquivo separado (`raw.pt.txt`, `improved.en.txt`, etc.). Não traduzir por cima do bruto.
- Idiomas alvo: o que o usuário pedir (português, inglês, espanhol, …). Se o modelo/Whisper não cobrir, dizer o limite.

O bruto original nunca é apagado quando há tradução.

## Saída

Diretório: `transcripts/<slug>/`

```
transcripts/<slug>/
  raw.txt              # sempre
  meta.json            # origem, método, duração, idioma detectado
  raw.srt              # se houver timestamps
  cleaned.txt          # se pediu limpeza sem IA
  improved.txt         # se pediu melhoria com IA
  raw.<lang>.txt       # se pediu outro idioma
  improved.<lang>.txt
  summary.txt          # se pediu resumo
```

`meta.json` guarda: path/URL de origem, método (`captions` | `whisper` | `text`), duração, idioma detectado, idioma pedido, tools usadas, timestamp.

No chat: prévia (primeiras ~80–120 palavras) + caminho completo dos arquivos. Se a transcrição for curta, o texto inteiro no chat além do arquivo.

## Arquitetura: pasta + tools, não um .md sozinho

```
transcribe-media/
  project.md                 # este arquivo — objetivo do projeto
  SKILL.md                   # quando implementar: quando disparar e como orquestrar
  tools/
    detect_source.py         # classifica arquivo / URL / texto
    extract_audio.py         # ffmpeg → wav/mp3
    fetch_captions.py        # yt-dlp legendas (YouTube, X, etc.)
    transcribe_audio.py      # Whisper API (chunk se > ~24 MB)
    normalize_text.py        # .txt / .srt / .vtt → bruto
    cleanup_text.py          # limpeza sem IA
    improve_text.py          # melhoria com IA (OpenAI)
    translate_text.py        # quando o idioma pedido ≠ original
    summarize_text.py        # resumo opcional
    write_output.py          # grava arquivos + devolve texto para o chat
  references/
    refine-prompt.md         # prompt editorial da melhoria com IA
```

Cada tool faz uma coisa e devolve dado estruturado (texto, path, meta). A skill chama na ordem do fluxo. Nenhuma tool “melhora” o bruto por conta própria.

`SKILL.md` ainda não existe. Este `project.md` é o contrato. A implementação vem depois.

## Chave

Tudo que chama modelo usa **uma** variável: `OPENAI_API_KEY`.

| Uso | Modelo (inicial) |
|---|---|
| Transcrição de áudio | `whisper-1` |
| Melhoria com IA | um chat model barato/rápido da OpenAI (definir na implementação) |
| Tradução / resumo | o mesmo chat model |

Sem a chave, a skill não inventa transcrição. Diz: falta `OPENAI_API_KEY`. Legendas via `yt-dlp` podem funcionar sem a chave; Whisper, melhoria, tradução e resumo não.

Não treinar modelo. Não baixar Whisper local nesta versão.

## Dependências

Já conhecidas do ecossistema Aisha; a skill pergunta antes de instalar qualquer uma:

- `ffmpeg` / `ffprobe` — extrair áudio e duração
- `yt-dlp` — URLs (YouTube, X, etc.) e legendas
- `openai` (Python) — Whisper + chat
- `.venv` do projeto, se existir, deve ser ativado antes de rodar as tools

## Fora de escopo (nesta versão)

- Integrar no WhatsApp da Aisha
- Diarização de falantes (nomear quem falou)
- Whisper local / modelo treinado pelo usuário
- Instalar pacotes ou baixar binários sem perguntar
- Editar o vídeo (legendas burn-in, corte, etc.)

## Critérios de sucesso

- Qualquer vídeo, mp3, opus, arquivo do X ou URL suportada vira transcrição bruta em arquivo + texto.
- Depois da transcrição, o usuário é perguntado (bruta, melhorada, limpa, idioma, timestamps, resumo), salvo quando a primeira mensagem já era inequívoca.
- O bruto continua no disco mesmo depois de melhorar, traduzir ou resumir.
- Sem `OPENAI_API_KEY`, falha explícita — não alucina fala.
- Tools isoladas: dá para testar `cleanup_text` sem chamar Whisper.
