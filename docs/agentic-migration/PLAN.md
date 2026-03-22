# Aisha: Migração para Agentic Loop

## Objetivo

Migrar o núcleo de orquestração da Aisha de um classificador if/elif manual para um agentic loop real com tool calling nativo da OpenAI Responses API.

## Antes vs Depois

### Antes (roteamento imperativo)
```
Mensagem → gpt-4.1-mini classifica (1 palavra) → if/elif → chama função Python
```
O modelo não sabe quais skills existem. O código decide por ele.

### Depois (agente com tools)
```
Mensagem → gpt-5.4 recebe todas as tools → decide quais chamar → loop executa → modelo responde
```
O modelo conhece todas as capacidades e orquestra autonomamente.

## Reversibilidade

`AGENTIC_MODE=false` (default) → código antigo intacto, sem nenhuma mudança de comportamento.
`AGENTIC_MODE=true` → novo agentic loop assume.

## Arquitetura

```
aisha/
  agent.py            -- agentic loop (run_agent) + AgentResult
  tools/
    __init__.py        -- TOOL_DEFINITIONS + execute_tool dispatcher
    reminder.py        -- wrappers para skills/reminder.py
    scheduled_task.py  -- wrappers para skills/scheduled_task.py
    youtube.py         -- wrapper para skills/youtube.py
    webpage.py         -- wrapper para skills/webpage.py
    video_download.py  -- wrapper para skills/video_download.py
    profile.py         -- wrapper para user_profile
```

## Tools definidas

| Tool | Tipo | Descrição |
|---|---|---|
| web_search | built-in OpenAI | Busca na web (decidida pelo modelo) |
| image_generation | built-in OpenAI | Geração/edição de imagem |
| create_reminder | custom function | Cria lembrete com data/hora |
| list_reminders | custom function | Lista lembretes ativos |
| cancel_reminder | custom function | Cancela lembrete por número |
| edit_reminder | custom function | Edita mensagem, data/hora ou recorrência de lembrete existente |
| create_scheduled_task | custom function | Cria tarefa agendada recorrente |
| list_scheduled_tasks | custom function | Lista tarefas agendadas |
| cancel_scheduled_task | custom function | Cancela tarefa agendada |
| analyze_youtube_video | custom function | Analisa vídeo do YouTube |
| read_webpage | custom function | Lê e processa página web |
| download_video | custom function | Baixa vídeo (YouTube/Twitter) |
| set_personal_context | custom function | Salva contexto pessoal do usuário |
| set_language | custom function | Muda idioma preferido |
| get_my_profile | custom function | Lista perfil completo do usuário |

## O que NÃO muda

- Nenhum arquivo em `skills/` é modificado (tools são wrappers finos)
- `session.py`, `user_profile.py`, stores — intactos
- Deduplicação, echo detection, whitelist — permanecem
- APScheduler e restauração de jobs no startup — permanece
- `handle_image` e `handle_document` — continuam no fluxo antigo (fase 2)
