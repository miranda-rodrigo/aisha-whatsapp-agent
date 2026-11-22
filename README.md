# Aisha

Um repositório para a assistente pessoal pelo WhatsApp, seu site e suas ferramentas de desenvolvimento.

## Onde trabalhar

| Componente | Diretório | Responsabilidade |
|---|---|---|
| Bot em produção | `apps/agent` | Webhook, tarefas, entrega no WhatsApp e persistência |
| Núcleo de conversas | `packages/chat-analysis` | ZIP, mensagens, mídias, IA e relatórios compartilhados |
| Playground | `apps/playground` | Testar o mesmo núcleo no computador, sem WhatsApp/Supabase |
| Site | `apps/website` | Site público e páginas legais |
| Launcher | `tools/whatsapp-launcher` | Abrir contas WhatsApp Web no macOS |
| Dados locais | `local/` | Exportações, resultados e caches; nunca versionar ou publicar |

## Começar

Requisitos: Python 3.11+ (produção 3.12), FFmpeg/FFprobe. Para o site: Node 22 e pnpm 10.11.0.

```sh
make setup
make check
make playground ZIP="/caminho/conversa.zip"
```

O playground é offline por padrão. Gera HTML, Markdown, JSON, PDF e resumo em uma nova pasta de `local/runs/`. Não carrega `.env` automaticamente. Para testar chamadas reais de IA:

```sh
cp apps/playground/.env.example local/playground.env
# Preencha somente a chave de desenvolvimento.
make playground ZIP="/caminho/conversa.zip" ARGS="--ai --env-file local/playground.env"
```

Use `ARGS="--no-pdf"` se não tiver Chromium instalado. Arquivos existentes nunca são sobrescritos. Falhas ficam em `summary.json`; o comando retorna código diferente de zero e preserva os resultados recuperáveis.

Para rodar o bot, copie `.env.example` para `.env`, preencha as credenciais e execute `make agent-dev`. Esse comando usa serviços externos conforme a configuração. Para o site, execute `pnpm install --frozen-lockfile` dentro de `apps/website`, depois `make website-dev`.

## Organização e publicação

- [Arquitetura](docs/architecture/overview.md)
- [Desenvolvimento e testes](docs/development/testing.md)
- [Deploy e rollback](docs/operations/deploy.md)
- [Migração dos projetos antigos](docs/operations/migration.md)
- [Launcher](tools/whatsapp-launcher/README.md)

O GitHub é `miranda-rodrigo/aisha`. O histórico de `what_an_analysis` foi incorporado; o código antigo fica acessível pelo Git, sem uma segunda implementação ativa. Documentos históricos ficam em `docs/archive` e podem descrever comportamentos antigos.
