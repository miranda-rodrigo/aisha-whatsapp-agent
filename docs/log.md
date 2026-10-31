# Log de preços e monetização

Registro das ideias de preço. Não é um plano de negócio fechado. Os custos de API entram aqui depois de medidos no exemplo real.

## Referência de mercado

O chatview.ai cobra por conversa, sem assinatura:

- PDF simples (texto e emoji): US$ 4,99
- Pacote de evidências para advogado: US$ 14,99
- Pacote de evidências mais resumo de IA: US$ 19,99
- Passe de 30 dias para vários chats do mesmo caso: US$ 19,99

O argumento deles é que o chat não sai do navegador. Eles não transcrevem áudio. A numeração de provas deles (Bates) é convenção americana. No Brasil, hash de arquivo não autentica a conversa: o STJ exige cadeia de custódia quando há dúvida. Não prometer validade jurídica.

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

Preenchido depois de rodar o exemplo da corretora.

| Etapa | Modelo | Volume | Custo estimado |
|---|---|---|---|
| Nível 1, transcrição | | | |
| Nível 2, comentários | | | |
| Nível 3, análise | | | |
| Total do exemplo | | | |
