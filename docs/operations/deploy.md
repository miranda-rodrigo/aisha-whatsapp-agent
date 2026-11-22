# Deploy e rollback

## Bot

Railway: projeto `Aisha-agent`, serviço `whatsapp-agent`, ambiente `production`. Manter o nome/domínio do serviço para não alterar o webhook da Meta. Repositório canônico `miranda-rodrigo/aisha`, branch `main`, raiz do build na raiz do repositório. `railway.json` seleciona Dockerfile e health check `/health`.

O container instala `packages/chat-analysis` e `apps/agent`; inicia `uvicorn aisha.app:app`. Não há migração do banco. Manter variáveis existentes e as flags `WHATSAPP_EXPORT_ENABLED` e `WHATSAPP_EXPORT_MEDIA_ENABLED`. Não ativar mídia implicitamente durante a reorganização.

Após CI verde e merge, acompanhar build e health check; verificar logs sem expor credenciais. Validação de entrega real exige envio controlado de ZIP pelo WhatsApp. Testes sintéticos de integração não comprovam recebimento no telefone.

## Site

Projeto Vercel `aisha`, ID `prj_Q5O5E3Mppy1irhKu6E8RCbZ2TKUV`. Raiz final `apps/website`, manter domínios e demais configurações. Conferir permissões da equipe antes de alterar. `wrangler.jsonc` é uma configuração histórica de Cloudflare; não criar um segundo deploy automaticamente.

## Rollback

Antes desta migração: commit `bc858b3cd947c2e547671a6cd7b380a1e333c3ba`; implantação Railway `e500e97f-49e9-410b-9149-c9ae57a2f84d`. Restaurar a implantação anterior em caso de regressão. Para rollback via Git, reverter a consolidação e repor a raiz do site em `website`. Não apagar estado do banco. Domínio do webhook e nomes das variáveis não mudam.

A renomeação GitHub preserva histórico e redirecionamentos, mas integrações devem apontar explicitamente para o nome novo.
