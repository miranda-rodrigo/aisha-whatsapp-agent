# Log de preços e monetização

Registro das ideias de preço. Não é um plano de negócio fechado. Os custos de API entram aqui depois de medidos no exemplo real.

## Referência de mercado

O chatview.ai cobra por conversa, sem assinatura:

- PDF simples (texto e emoji): US$ 4,99
- Pacote de evidências para advogado: US$ 14,99
- Pacote de evidências mais resumo de IA: US$ 19,99
- Passe de 30 dias para vários chats do mesmo caso: US$ 19,99

O argumento deles é que o chat não sai do navegador. Eles não transcrevem áudio. A numeração de provas deles (Bates) é convenção americana. No Brasil, hash de arquivo não autentica a conversa: o STJ exige cadeia de custódia quando há dúvida. Não prometer validade jurídica.

## Âncoras de preço no Brasil (pesquisa de 31/10/2026)

O que o advogado já paga hoje, segundo a pesquisa em `pesquisa/deep-research-report.md`:

- Verifact, relatório de WhatsApp: R$ 97 por relatório.
- Ata notarial em São Paulo, 2026: R$ 237,22 a primeira página, mais as seguintes. Minas Gerais: R$ 218,42 até duas páginas.
- Jus IA (Jusbrasil): R$ 78,90, R$ 108,90 e R$ 208,90 por mês. Já transcreve áudio de WhatsApp, um arquivo por vez.
- Jusfy: R$ 77, R$ 117 e R$ 227 por mês. Também transcreve áudio.
- Astrea: R$ 209 a R$ 1.249 por mês.

Proposta de teste vinda da pesquisa (é estimativa, não fato de mercado):

| Oferta | Preço de teste | Por quê |
|---|---|---|
| Um dossiê | R$ 59 | Abaixo do Verifact e da ata, bem acima do custo de API (~R$ 3,70) |
| Pacote de 5 casos | R$ 199 | Testa uso repetido sem exigir assinatura |
| Escritório | R$ 349/mês com ~15 dossiês | Dentro da faixa que advogado já paga por software |
| API / white label | Sob consulta | Só depois de haver uso repetido |

A pesquisa desaconselha começar em R$ 9,90–19,90: o preço deve ser ancorado na hora do advogado poupada, não no custo de API. Discordância a testar: R$ 59 por dossiê compete com R$ 78,90/mês do Jus IA, que faz parte do trabalho. O argumento de venda precisa ser o que o Jus IA não faz (conversa inteira, citação por mensagem), senão o advogado compara só o preço.

Primeiro experimento sugerido: dossiê "concierge" pago. Recrutar 15–20 advogados, processar um caso real anonimizado ou encerrado e cobrar os R$ 59. Medir se pagam, quanto tempo levam para conferir, quantas correções fazem e se mandam um segundo caso em 30 dias.

## Ideia: os níveis do produto são os planos

Cada nível acrescenta uma camada e custa mais para produzir. O preço ao cliente pode seguir a mesma escada.

| Nível | O que o cliente recebe | Custo nosso | Preço pensado |
|---|---|---|---|
| 0 | Conversa legível, imagens no lugar, players de áudio e vídeo | Zero de API | Grátis, ou a porta de entrada |
| 1 | Transcrição fiel de cada áudio, ao lado do player | Minutos de áudio | Plano barato |
| 2 | Comentário contextualizado em cada imagem, PDF e áudio | Chamadas de visão e texto | Plano intermediário |
| 3 | Resumo, linha do tempo, valores, compromissos e pendências, cada um citando a mensagem | Uma análise sobre o dossiê | Plano completo |

A transcrição fiel nunca é reescrita. Uma versão "limpa" da fala, se existir um dia, fica como camada separada e não substitui o texto fiel. Em uso jurídico, só o fiel conta.

## Quem pagaria

Hipótese, ainda sem entrevista:

- Advogados (trabalhista, família, consumidor): organizar o WhatsApp do cliente, sobretudo os áudios. Faixa chutada de R$ 50 a R$ 150 por caso, pagamento único.
- Arquitetos, corretores e empreiteiros: dossiê do que o cliente aprovou, quando e o que mudou.
- Uso pessoal (entender uma conversa) existe, mas parece esporádico e pouco recorrente.

Forma de cobrança mais plausível, copiando o que já vende: pagamento avulso por conversa, ou um passe por caso quando há vários chats. Assinatura mensal não combina com um uso que acontece uma vez por processo.

O produto complementa quem autentica a prova (ata notarial, Verifact). Eles capturam. Nós organizamos e lemos.

## O que ainda trava o preço

- Custo real de API por conversa. A estimativa para o exemplo da corretora (22 minutos de áudio, 50 imagens, 7 PDFs) era centavos na transcrição e menos de US$ 1 no restante. Os números medidos entram na seção abaixo.
- Parte das mídias some da exportação quando o arquivo não está mais no celular. O preço não pode prometer "todas as fotos".
- A partir do nível 1 o conteúdo vai para a API. O cliente precisa saber disso antes de pagar. Conversas com documentos (contrato, fatura, dados bancários) são o caso sensível.

## Custos medidos

Exemplo da corretora (398 mensagens, 57 áudios = 21,7 min, 50 imagens, 7 PDFs), medido em 31/10/2026. Pipeline completo rodou em ~39 s com 10 chamadas em paralelo.

| Etapa | Modelo | Volume | Custo estimado |
|---|---|---|---|
| Nível 1, transcrição | gpt-4o-mini-transcribe | 57 áudios, 21,7 min | US$ 0,038 |
| Nível 2, comentários | gpt-4o-mini | 114 mídias (áudio+imagem+PDF) | US$ 0,62 |
| Nível 3, análise | gpt-4o-mini | 1 chamada | US$ 0,006 |
| Total do exemplo | | 172 chamadas | **US$ 0,66** |

Leitura para o preço: o custo variável de um dossiê completo desta conversa é ~R$ 3,70. O nível 2 domina o custo porque envia a conversa inteira como contexto em cada uma das 114 chamadas; dá para reduzir bastante com janela de contexto menor ou cache de prompt, se um dia importar. Com preço de R$ 50–150 por caso, a margem bruta é confortável; o custo relevante do produto não é API, é aquisição de cliente.
