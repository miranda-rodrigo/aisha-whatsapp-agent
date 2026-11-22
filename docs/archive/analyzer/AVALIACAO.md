# Avaliação: nosso dossiê vs. Zap2Doc vs. texto cru

Etapa 7 da Fase 1. Pergunta que o teste responde: **uma IA responde melhor sobre a conversa quando recebe o nosso `conversa.md` do que quando recebe o PDF do Zap2Doc (R$ 19,90) ou o `_chat.txt` cru?** Se a diferença for pequena, os níveis 2 e 3 não justificam preço e o nicho precisa ser repensado.

Conversa usada: corretora de planos (398 mensagens, 57 áudios, 50 imagens, 7 PDFs).

## Entradas

| Id | Arquivo | Quem gera |
|---|---|---|
| A | `_chat.txt` cru da exportação | WhatsApp |
| B | PDF do Zap2Doc (e a cópia em Markdown, se vier) | Rodrigo, em zap2doc.com |
| C | `output/.../conversa.md` (com análise e comentários) | nosso `build --nivel 3` |
| C2 (opcional) | `conversa.md` sem a seção "Análise" | apagar a seção à mão |

C2 isola uma dúvida: a seção de análise ajuda ou atrapalha? Ela tem pelo menos um erro conhecido (lista R$ 1.074,27 como valor da Unimed e não menciona os R$ 852,45 contratados).

Cuidado com privacidade: a conversa tem RG, fatura com endereço, contrato social e informação de saúde (dado sensível pela LGPD). Subir no Zap2Doc e no ChatGPT envia isso a terceiros. O Zap2Doc diz apagar a exportação em 24 h. A decisão é do Rodrigo.

## Procedimento

1. Mesmo modelo para todas as entradas (anotar qual, ex.: ChatGPT com GPT-5). Um chat novo e temporário por entrada, sem memória.
2. Anexar só o arquivo da entrada e colar o prompt abaixo, com as 12 perguntas de uma vez.
3. Salvar a resposta em `data/avaliacao/<id>.md` (fora do Git).
4. Corrigir com a tabela de respostas esperadas.

Prompt:

```
Anexei o registro de uma conversa de WhatsApp entre um cliente (Rodrigo) e uma corretora de planos de saúde (Emanuella).
Responda às 12 perguntas abaixo usando somente o arquivo.
Para cada resposta, diga de onde tirou: data e hora da mensagem (e o id msg-..., ou a página, se o arquivo tiver).
Se a informação não estiver no arquivo, responda "não encontrado". Não deduza.
[colar as 12 perguntas]
```

## Pontuação

Por pergunta:

- **Resposta:** 2 = correta e completa; 1 = parcial; 0 = errada ou "não encontrado" quando a informação existe.
- **Fonte:** 1 se a fonte indicada existe e sustenta a resposta; 0 se não.
- **Invenção:** marcar quando a IA afirma algo que não está na conversa.

Máximo por entrada: 24 pontos de resposta + 12 de fonte. Anotar também o tempo para conferir as respostas.

## Perguntas candidatas

Fonte da resposta: T = texto, A = áudio, I = imagem, P = PDF. O Rodrigo precisa confirmar as respostas esperadas; foram tiradas da transcrição e dos comentários e podem ter erro.

| # | Pergunta | Resposta esperada | Fonte |
|---|---|---|---|
| 1 | Quais planos foram cotados em 29/09 e quanto custava cada um? | Best Senior R$ 762,18 sem coparticipação; Unimed R$ 1.074,27 com coparticipação; São Camilo R$ 716,43; Liv Saúde R$ 478,72; Hapvida R$ 653,05 | I + A |
| 2 | Qual plano a corretora apontou como o de melhor qualidade e qual como o mais barato? | Best Senior (melhores hospitais); Liv Saúde (mais barato) | A |
| 3 | Quanto custava o Best Senior **com** coparticipação? | R$ 624,99 | só I |
| 4 | Que documentos foram pedidos para o aproveitamento de carência? | Foto da carteirinha do plano atual e carta/declaração de permanência do Bradesco | T + A |
| 5 | Qual o número da proposta do Best Senior e o que aconteceu com ela? | 38860; não foi aprovada (14/10), por pré-existência após a auditoria | T + A |
| 6 | Segundo a corretora, qual a carência para doença pré-existente na Unimed? | 24 meses para o que for relacionado ao diagnóstico informado | só A |
| 7 | Qual plano e valor foram contratados no fim? | Unimed empresarial, enfermaria, com coparticipação, R$ 852,45 (baixou de R$ 1.074,27) | T + A + I |
| 8 | Como funciona a coparticipação do plano contratado? | 30% sobre a tabela da Unimed; internações e cirurgias sem coparticipação; cobrada na fatura em 30–60 dias | A + I |
| 9 | Qual a regra de multa por cancelamento, e que contradição o Rodrigo apontou? | No áudio: percentual da mensalidade vezes os meses que faltam para 1 ano. No texto: 3 vezes a média das faturas. Rodrigo apontou a diferença; ela disse que, por ser contrato empresa de um usuário, vale o texto (média das últimas faturas) | T + A |
| 10 | O Rodrigo desistiu do plano em algum momento? Quando e por quê? | 16/10 disse que ia repensar (áudio); 21/10 decidiu não fazer (não assumir outro gasto, sem emprego, momento de depressão); 27/10 pediu mais uns dias; 29/10 fez a entrevista | T + A |
| 11 | A partir de quando o plano vale? | Contrato com início em 30/10, mas só valida após o pagamento (feito em 30/10); carteirinha provável na terça seguinte, por causa do feriado. Antes tinha sido prometido uso em 01/11 | T + A |
| 12 | O que ficou sem resposta no fim da conversa? | A pergunta do Rodrigo de 31/10: por que foi aplicado aproveitamento comercial de carências e não portabilidade formal do Bradesco | T |

As perguntas 3 e 6 são as mais reveladoras: a resposta está só numa imagem (3) ou só num áudio (6). O texto cru não tem nenhuma das duas. O Zap2Doc deve acertar a 6 (transcreve) e talvez não a 3 (depende de a IA ler a imagem no PDF).

## Resultado

Respostas brutas em `data/avaliacao/` (fora do Git). O PDF do Zap2Doc está em `docs/competidores/` e também fica fora do Git, porque contém os documentos pessoais da conversa.

### B: Zap2Doc + ChatGPT (perguntas 1–7, em 31/10)

| # | Resposta | Fonte | Observação |
|---|---|---|---|
| 1 | 2 | 1 | Mais completa que o esperado: leu também os valores com coparticipação nas imagens. Único erro: Best Senior com coparticipação R$ 624,90 (a imagem diz 624,99) |
| 2 | 2 | 1 | Citou o áudio das 13h57 |
| 3 | 1 | 1 | R$ 624,90; o correto é R$ 624,99 (conferido na imagem `00000078`) |
| 4 | 2 | 1 | |
| 5 | 1 | 1 | Número e recusa corretos, mas disse que "a conversa não esclarece o motivo"; o áudio de 14/10 20:20 explica (pré-existência) |
| 6 | 2 | 0 | Correta, sem indicar fonte |
| 7 | 2 | 1 | R$ 852,45, enfermaria, coparticipação 30%. A nossa seção de análise erra justamente esse ponto |
| **Parcial** | **12/14** | **6/7** | Nenhuma invenção grave |

Ressalvas do teste:
- O chat não era temporário: o ChatGPT reconheceu o projeto ("parece ser um exemplo real do dossiê produzido pela sua ferramenta"). Usar chat temporário nas próximas rodadas.
- Faltam as perguntas 8 a 12. A 9 (contradição áudio × texto) e a 12 (pergunta sem resposta) são as mais difíceis.

O que o PDF do Zap2Doc traz (79 páginas): cabeçalho com período, contagem de mensagens e anexos, SHA-256 da exportação e horário de recebimento; legenda; data e hora por mensagem; 1.942 imagens embutidas, inclusive as primeiras 4 páginas de cada PDF anexado como miniatura; páginas numeradas. Conta 390 mensagens (nós, 398: a diferença deve ser mensagens de sistema).

### Placar

| Entrada | Resposta (0–24) | Fonte (0–12) | Invenções | Tempo para conferir |
|---|---|---|---|---|
| A | | | | |
| B | 12/14 (parcial) | 6/7 (parcial) | 0 | |
| C | | | | |
| C2 | | | | |
