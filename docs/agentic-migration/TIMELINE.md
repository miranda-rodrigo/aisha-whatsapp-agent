# Timeline da Migração para Agentic Loop

## Fase 1 — Núcleo agêntico (atual)

### [2026-03-20] Início da migração

**Branch:** `feature/agentic-loop`

**Escopo:**
- Feature flag `AGENTIC_MODE` em config.py
- Camada `aisha/tools/` com wrappers para todas as skills
- `aisha/agent.py` com agentic loop completo
- Integração em `app.py` com desvio condicional

**Decisões tomadas:**
- Não usar frameworks (LangGraph, CrewAI) — implementação manual para aprendizado e controle total
- Não modificar nenhum arquivo em `skills/` — tools são wrappers finos
- Feature flag para reversibilidade instantânea
- gpt-5.4 como modelo único do agente (já usado para COMPLEX hoje)
- Max 10 iterações no agentic loop como safety net

**Status:** Implementado

**Arquivos criados:**
- `aisha/config.py` — adicionado `AGENTIC_MODE` (default `false`)
- `aisha/agent.py` — agentic loop com max 10 iterações, modelo gpt-5.4
- `aisha/tools/__init__.py` — 14 tool definitions + dispatcher `execute_tool`
- `aisha/tools/reminder.py` — wrappers create/list/cancel
- `aisha/tools/scheduled_task.py` — wrappers create/list/cancel
- `aisha/tools/youtube.py` — wrapper analyze_video
- `aisha/tools/webpage.py` — wrapper read_webpage + fetch
- `aisha/tools/video_download.py` — wrapper download + link temporário
- `aisha/tools/profile.py` — wrappers set_context/set_language/get_profile

**Arquivos modificados:**
- `aisha/app.py` — `handle_chat` desvia para `_handle_chat_agentic` quando `AGENTIC_MODE=true`. `handle_audio` desvia a parte de chat para `run_agent`. Código legacy intacto em `_handle_chat_legacy`.

**Validação:**
- Todos os imports funcionam (verificado com `python -c`)
- 14 tools carregam corretamente
- `AGENTIC_MODE=False` por padrão (sem risco de quebrar produção)
- Zero erros de linter

### [2026-03-21] Primeiro teste em produção — sucesso

**Deploy:** Railway apontado para `feature/agentic-loop`, variável `AGENTIC_MODE=true`

**Resultados do teste (conversa real via WhatsApp):**

| Cenário testado | Resultado | Tools chamadas |
|---|---|---|
| Chat simples ("oi, tudo bem?") | OK — resposta natural | nenhuma |
| Listar lembretes | OK — retornou lista vazia corretamente | `list_reminders` |
| Perguntar capacidades | OK — listou todas as skills disponíveis | nenhuma (respondeu do system prompt) |
| Listar tarefas agendadas | OK — mostrou tarefa existente | `list_scheduled_tasks` |
| Cancelar tarefa agendada | OK — cancelou corretamente | `cancel_scheduled_task` |
| Áudio com "Aisha" (chat por voz) | OK — respondeu + salvou contexto pessoal | `set_personal_context` |
| Áudio sem "Aisha" (transcrição) | OK — transcreveu normalmente | nenhuma (fora do agente) |
| Criar lembrete com pesquisa ("me lembra + pesquise endereço") | OK — multi-tool no mesmo turno | `create_reminder` + `web_search` |
| Link do X/Twitter (leitura) | OK — resumiu o post | `read_webpage` |
| Download de vídeo do X | OK — gerou link temporário | `download_video` |
| **Intenção composta** ("pesquisa sobre IA generativa e me lembra de revisar amanhã") | **OK** — executou ambas as intenções | `web_search` + `create_reminder` |

**Observações qualitativas:**
- O modelo sugere próximas ações proativamente (antes não fazia)
- A consciência de todas as tools no system prompt melhora a coerência das respostas
- Latência aceitável (respostas em ~5-10s para chamadas com tools)
- A intenção composta funcionou de primeira — era impossível no sistema antigo

**Problemas encontrados:** Nenhum

---

## Fase 1.5 — Pendente: merge na main

- [ ] Merge da branch `feature/agentic-loop` na `main` via Pull Request
- [ ] Railway volta a apontar para `main`
- [ ] Remover código legacy (`_handle_chat_legacy`) após período de estabilidade

---

## Fase 2 — Planejada

- Migrar `handle_image` e `handle_document` para o agente (input multimodal)
- Persistir `pending_states` no Supabase
- Observabilidade (logs estruturados por interação)

## Fase 3 — Futuro

- Sistema de usuários + rate limiting para abrir uso público
- Memória semântica de longo prazo (avaliar Mem0 ou embeddings no Supabase)
