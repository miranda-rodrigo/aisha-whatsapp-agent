# Consolidação — 22/11/2026

| Antes | Agora |
|---|---|
| Pasta `whatsapp-agent`; GitHub `aisha-whatsapp-agent` | Pasta `aisha`; GitHub `aisha` |
| Projeto Codex `chat-analysis-skill-aisha` | Mesmo projeto Aisha; não era outro checkout |
| `chat_analysis_whatsapp` / `what_an_analysis` | Núcleo compartilhado + playground |
| `whatsapp-launcher/whatsapp-launcher` | `tools/whatsapp-launcher` |
| `website` | `apps/website` |

Backup completo verificado com SHA-256: `~/useful-repos/.aisha-migration-backups/20261122-190252/`. O manifesto lista hashes por arquivo. As pastas originais só devem ser arquivadas após validação; não são necessárias para instalar a nova árvore.

Os dois commits de mídias, as alterações locais do bot e o histórico do analisador foram preservados antes da reorganização. O commit de importação local do analisador contém sua última versão completa. A antiga interface `wa_dossier` foi aposentada; o playground testa a implementação de produção, sem um segundo pipeline. Funcionalidades exclusivas do protótipo (por exemplo, comentário de documentos) permanecem recuperáveis no histórico, não são anunciadas como capacidades atuais do bot.

Relatórios reais, áudios de experimentos, configuração de número e apresentações locais foram preservados em `local/`. Os dados do analisador estão em `local/legacy-analyzer`. Arquivos já presentes no histórico antigo não são apagados do histórico por esta migração; não houve force-push.

Antes da migração, a execução da suíte retornou 2 falhas e 35 erros (incluindo erros de permissão ao abrir logs no sandbox). Mocks antigos de clientes HTTP, execução de tarefas e prazo de downloads precisam acompanhar as interfaces atuais. As mudanças nesses testes não alteram o comportamento do produto.

A configuração de publicação e a organização do Codex devem ser verificadas no encerramento; não confundir arquivos locais prontos com deploy concluído.
