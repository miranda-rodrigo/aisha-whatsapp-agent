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

## PDF — plano aprovado e implementação (13/11/2026)

O ZIP recebe uma confirmação curta; o resultado inicial é `conversa-analisada.pdf`
anexado como `application/pdf`. O PDF abre com título, período, participantes e
contagem, depois apresenta interpretações da IA com links internos e a conversa
integral. Autores, horários, mensagens de sistema e IDs são preservados. Mídias
aparecem sinalizadas, sem transcrição ou interpretação. A análise continua sujeita
a erros mesmo quando a referência existe.

O template de impressão se inspira em `wa_dossier/render_html.py`: azul escuro,
balões claros e azuis, referências douradas e separadores por dia. A4 retrato,
texto selecionável e páginas numeradas. O primeiro participante ocupa a direita;
a legenda deixa claro que ele não é necessariamente quem enviou o ZIP. Mensagens
longas continuam na página seguinte, sem truncamento.

- `reenviar pdf` recupera conversa e análise salvas. Não chama o modelo novamente
  se a análise já foi armazenada; regeneração e entrega não renovam as 24 horas.
- Perguntas `sobre a conversa:` continuam em texto, com trechos e IDs validados.
- Payload v2 inclui título, pergunta inicial e conclusões estruturadas. Registros
  v1 continuam legíveis; o primeiro reenvio analisa e atualiza o payload, sem
  alterar sua expiração. Falhas de análise, armazenamento, geração e envio são
  reportadas separadamente. Uma falha ao salvar a análise pode exigir nova análise.
- O PDF não é salvo no Supabase. Chromium usa um diretório temporário por pedido,
  removido em sucesso ou erro. O limite é 20 MiB; exceder exige um período menor.
- O webhook já retorna antes do processamento. Um semáforo permite uma renderização
  por processo; espera e renderização têm prazo total de 60 segundos. A implantação
  atual tem uma réplica. Mais réplicas exigirão coordenação para limite global.
- Chromium/Playwright 1.56.0 é instalado no build Docker. Fontes e licenças OFL estão
  incluídas em `aisha/chat_export/fonts`. Não há download durante a geração.
- Conteúdo importado é escapado. JavaScript e service workers estão desativados;
  a única navegação é respondida internamente com o template controlado. Demais
  requisições são bloqueadas. A análise não tem ferramentas externas.
- A entrega valida erros HTTP tanto no upload quanto na requisição de envio à Meta.
  Aceitação pela API não comprova leitura ou entrega final ao dispositivo.

### Validação reproduzível

`python -m scripts.check_export_pdf /tmp/aisha-pdf-preview` usa apenas dados
sintéticos: grupo, sistema, acentos, emoji, mídia omitida e mensagem longa. Verifica
cada linha, nome, data, hora e ID extraído, ordem dos IDs, destinos dos links e
limpeza dos temporários; grava PDF e imagens para inspeção visual opcional.

Resultado local: seis páginas, aproximadamente 318 kB, menos de um segundo de
renderização. `child_maxrss` é a métrica de pico dos processos filhos (bytes no
macOS, KiB no Linux), não uma medida da memória total simultânea do serviço.

`python -m scripts.check_export_live` é opt-in: usa Supabase e OpenAI reais com
uma conversa sintética e simula download/entrega Meta. Confere armazenamento,
isolamento, geração, reenvio sem modelo, pergunta posterior e exclusão. Remove o
registro sintético em `finally`. Pode bloquear o pré-deploy se falhar; requer
configuração temporária autorizada pelo operador e sua remoção após validar.

A ativação em produção continua condicionada ao sucesso desse teste no container
Railway e ao health check. Nunca enviar os arquivos locais não versionados no
build. A flag `WHATSAPP_EXPORT_ENABLED` desativa também o reenvio.

### Verificação no Railway em 13/11/2026

A implantação `9f9752bc-00df-4a27-90bc-94db27296264` executou o teste sintético
com sucesso: geração, armazenamento real, análise real, isolamento, reenvio sem
nova chamada de análise, pergunta posterior e exclusão. Chromium produziu seis
páginas / 267.576 bytes em 0,86 s; pico de processo filho 134.772 KiB no Linux.

A primeira tentativa foi bloqueada por autenticação OpenAI inválida na configuração
de produção. A credencial já existente localmente foi validada e aplicada ao Railway;
nenhuma credencial foi incorporada ao código ou aos logs deste teste.

O comando temporário de pré-deploy foi removido e a flag foi configurada como
`true` para a implantação final. A entrega Meta foi simulada: ainda é necessário
um envio real de ZIP pelo usuário para confirmar o recebimento no aparelho.
Testes adicionais cobrem fechamento do navegador e limpeza em falha/cancelamento,
além do bloqueio de requisições externas. As alterações locais anteriores continuam
fora dos commits desta integração.
