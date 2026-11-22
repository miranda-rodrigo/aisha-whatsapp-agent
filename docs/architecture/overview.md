# Arquitetura

```text
WhatsApp -> apps/agent -> packages/chat-analysis -> IA e PDF
                         ^
ZIP local -> apps/playground

apps/website              site independente
 tools/whatsapp-launcher   utilitário independente de macOS
```

O pacote `aisha_chat` é a única implementação ativa de leitura de exportações, IDs, processamento de mídias, análise e template PDF. Não importa `aisha`, não exige Supabase e só cria cliente de IA quando necessário.

O bot mantém `aisha.chat_export` como camada de compatibilidade e configuração: handler, armazenamento e assets privados pertencem ao serviço. Imports antigos encaminham aos módulos compartilhados, preservando APIs, patches de teste e payloads v1/v2/v3 já armazenados. `configure_storage` injeta os adaptadores uma vez na inicialização de cada processo; não trocar backends durante requisições.

O playground usa adaptadores de arquivos em uma pasta exclusiva por execução. Não importa o bot, não envia mensagens e não acessa banco de produção. Os modelos padrão acompanham o registro do bot; variáveis `AISHA_*` permitem testes explícitos. Não há sincronização automática de arquivos entre repositórios.

Os limites de produção valem também no playground: ZIP 50 MiB, texto 2 MiB, contexto textual 100 mil caracteres e enriquecido 200 mil; até 200 áudios/60 minutos e 40 imagens. Documentos anexados são identificados, não analisados. Mídias ausentes e falhas são sinalizadas. Melhorias futuras entram no núcleo e são testadas nas duas interfaces.

O bot é instalado como pacote Python; o Docker copia apenas o serviço, o núcleo e scripts operacionais. O site usa build separado. O Launcher não é dependência do servidor.
