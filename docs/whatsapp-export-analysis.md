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

## Uso e operação

- Ativar com `WHATSAPP_EXPORT_ENABLED=true`; o padrão é `false`. Desativar a
  flag interrompe novas análises; `esquecer conversa` continua disponível.
- Enviar ZIP exportado pelo WhatsApp, opcionalmente com uma pergunta na legenda.
  Receber conclusões com IDs, autor, data, hora e trechos originais.
- Perguntar `sobre a conversa: qual foi o combinado?`. Só a conversa do remetente
  é consultada. Um novo ZIP válido substitui o anterior; a expiração não se
  renova a cada pergunta.
- `esquecer conversa` remove o registro ativo no Supabase. Não apaga mensagens
  já entregues pelo WhatsApp nem dados sujeitos às políticas do provedor de IA.
- A expiração de 24 horas bloqueia acesso; exclusão física ocorre quando o registro
  expirado é consultado, quando é substituído ou quando o usuário pede exclusão.
- A aplicação não guarda o ZIP ou extrai mídias. O texto normalizado fica em
  `pending_states`, tipo `wa_export`, payload versionado. Sem cache local;
  consultas sobrevivem a reinícios. Falhas do banco são mostradas ao usuário.
- O parser e o algoritmo de IDs vêm de `wa_dossier`, commit `da9ad53` do projeto
  `chat_analysis_whatsapp`. O código necessário está incluído em `aisha/chat_export`.
- Conversas com datas numéricas separadas por `/` nos formatos suportados de
  iPhone/Android são aceitas; outros formatos/localidades podem ser rejeitados.
- Além dos limites principais, no máximo 10 mil entradas por ZIP. Todos os `.txt`
  candidatos juntos respeitam 2 MiB. Múltiplos chats são rejeitados.
- IDs válidos não comprovam que a conclusão é correta. As fontes são renderizadas
  pelo código a partir da conversa; afirmações sem IDs válidos são descartadas.

## Verificação em 12/11/2026

- 43 testes focados em exportações, roteamento, handlers e documentos passaram.
- A suíte geral já tinha 2 falhas e 32 erros; reproduzidos numa cópia do estado
  anterior à integração (203 testes). Incluem mocks HTTP desatualizados e registro
  de downloads. Não foram incluídas correções não relacionadas nesta branch.
- Supabase: consulta das colunas de `pending_states` retornou HTTP 200. Um registro
  sintético foi salvo, recuperado e apagado com sucesso.
- OpenAI: uma pergunta sintética gerou resposta com referência válida.
- Railway: projeto Aisha-agent, serviço whatsapp-agent, ambiente production,
  fonte GitHub `miranda-rodrigo/aisha-whatsapp-agent`, branch `main`.

## Publicação e rollback

Publicar somente os commits da branch de integração via PR para main. Não enviar
o diretório de trabalho inteiro, pois contém mudanças anteriores não relacionadas.
Após deploy, verificar `/health`, executar teste sintético no container e ativar
`WHATSAPP_EXPORT_ENABLED=true`. Para rollback funcional, definir a flag como false
(e aplicar o redeploy); para rollback de código, usar a implantação anterior.
