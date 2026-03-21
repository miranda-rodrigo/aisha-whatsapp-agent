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

---

## Fase 2 — Planejada

- Migrar `handle_image` e `handle_document` para o agente (input multimodal)
- Persistir `pending_states` no Supabase
- Observabilidade (logs estruturados por interação)

## Fase 3 — Futuro

- Sistema de usuários + rate limiting para abrir uso público
- Memória semântica de longo prazo (avaliar Mem0 ou embeddings no Supabase)
