# Análise de exportações na Aisha

## Plano aprovado

Integrar o parser iPhone/Android e IDs de mensagens do wa_dossier como módulo
interno, sem dependência de outro checkout ou serviço. Receber ZIP no WhatsApp,
ler somente texto em memória e gerar análise sem ferramentas, com referências
validadas e trechos originais. Mídias ficam fora desta versão.

Limites: ZIP de 50 MiB, texto descompactado de 2 MiB, conversa formatada de
100 mil caracteres. Rejeitar formatos inválidos, criptografia, ambiguidade e
excessos sem truncar silenciosamente.

Persistir uma conversa por remetente em pending_states, por 24 horas. Perguntar
com `sobre a conversa: ...`; apagar com `esquecer conversa`. Só substituir a
conversa anterior após validação e armazenamento bem-sucedidos.

Testar parser, limites, citações, isolamento entre usuários, expiração, falhas
de serviços e handlers com dados sintéticos. Commits por etapa, sem incluir
alterações preexistentes. Conferir Supabase e Railway antes da publicação,
com feature flag para ativação e rollback.
