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

### [2026-03-21] Merge na main

- [x] Merge da branch `feature/agentic-loop` na `main` (fast-forward, sem conflitos)
- [x] Push para GitHub — Railway faz redeploy automático da `main`
- [ ] Apontar Railway de volta para `main` (se estava apontado para a branch)
- [ ] Remover código legacy (`_handle_chat_legacy`) após período de estabilidade

---

### [2026-03-22] Correção: lembretes duplicados em follow-ups

**Problema identificado em produção:**

Quando o usuário enviava duas mensagens sobre o mesmo lembrete em sequência — a primeira criando e a segunda refinando (ex: pedindo para incluir o endereço) — o sistema criava dois lembretes distintos. O motivo: o agente não sabia quais lembretes já existiam, então classificava o follow-up como uma nova criação.

**Diagnóstico via logs do Railway:**
- Dois lembretes da igreja dispararam simultâneamente às 11:45 UTC: `4bde967e` ("Ida à igreja AD Zona Sul") e `6fd5b3a1` ("Ida à igreja Assembleia de Deus Zona Sul")
- Confirmado que ambos foram inseridos como registros independentes via chamadas separadas a `create_reminder`

**Solução implementada (3 camadas):**

1. **Tool `edit_reminder`** — nova tool que permite atualizar data/hora, mensagem ou recorrência de um lembrete existente pelo número. Evita a necessidade de cancelar + recriar.

2. **Lembretes ativos no system prompt** — a cada chamada ao agente, os lembretes pendentes do usuário são buscados e injetados no `instructions` do modelo. O modelo passa a ver o que já existe antes de decidir criar ou editar.

3. **Instrução de não-duplicata** — a descrição de `create_reminder` agora instrui explicitamente o modelo a verificar os lembretes ativos antes de criar, e a preferir `edit_reminder` se o assunto já existe.

**Arquivos modificados:**
- `aisha/tools/reminder.py` — adicionada `tool_edit_reminder`
- `aisha/tools/__init__.py` — registrada `edit_reminder` em `TOOL_DEFINITIONS` e `_DISPATCH`; instrução de `create_reminder` atualizada
- `aisha/agent.py` — `run_agent` busca lembretes ativos e passa para `_build_system_prompt`; `_build_system_prompt` recebe e serializa a lista no `instructions`

---

## Fase 2 — Planejada

- Migrar `handle_image` e `handle_document` para o agente (input multimodal)
- Persistir `pending_states` no Supabase
- Observabilidade (logs estruturados por interação)

## Fase 3 — Futuro

- Sistema de usuários + rate limiting para abrir uso público
- Memória semântica de longo prazo (avaliar Mem0 ou embeddings no Supabase)
