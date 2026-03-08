# Aisha — Guia de Habilidades

Tudo que a Aisha sabe fazer e como usar cada funcionalidade.

---

## 1. Conversa

A Aisha é uma assistente conversacional. Qualquer mensagem de texto vai direto para o chat — sem comandos especiais.

**Como usar:**
```
Você: oi, tudo bem?
Aisha: Oi! Tudo ótimo, e você?

Você: me explica o que é juros compostos
Aisha: Claro! Juros compostos são...

Você: qual a diferença entre Python e JavaScript?
Aisha: As principais diferenças são...
```

**Contexto de conversa:**
- A Aisha lembra do que foi dito nos últimos **10 minutos** de inatividade
- Depois de 10 min sem mensagem, a conversa recomeça do zero automaticamente
- Para resetar manualmente: diga `nova conversa`, `novo assunto`, `mudar de assunto` ou `reset`

---

## 2. Transcrição de Áudio

Envie um áudio **sem mencionar "Aisha"** e ele será transcrito, limpo e devolvido como texto.

**Como usar:**
- Grave e envie qualquer áudio no WhatsApp
- A Aisha devolve o texto refinado, sem vícios de linguagem ou hesitações

**Ideal para:**
- Transcrever reuniões, anotações em voz, mensagens longas
- Transformar um áudio recebido em texto

---

## 3. Chat por Áudio

Envie um áudio **mencionando "Aisha"** para conversar com ela por voz.

**Como usar:**
```
[áudio] "Aisha, qual é a previsão do tempo para amanhã?"
[áudio] "Aisha, me resume esse conceito de machine learning"
[áudio] "Aisha, deixa essa mensagem mais formal: [ditado]"
```

A palavra "Aisha" no início (ou em qualquer parte) do áudio indica que é uma conversa, não uma transcrição.

---

## 4. Busca na Web

A Aisha busca informações atualizadas automaticamente quando precisa. Não é necessário nenhum comando — ela decide sozinha quando usar.

**Como usar:**
```
Você: quem ganhou o Oscar de melhor filme esse ano?
Você: qual o dólar hoje?
Você: últimas notícias sobre o mercado financeiro
Você: qual o resultado do jogo do Flamengo ontem?
```

---

## 5. Geração de Imagem

A Aisha gera imagens e as envia direto no WhatsApp. Basta pedir.

**Como usar:**
```
Você: gera uma imagem de um cachorro astronauta
Você: cria uma logo minimalista para uma startup de tecnologia
Você: faz uma ilustração de uma cidade futurista ao anoitecer
Você: me faz uma imagem no estilo aquarela de montanhas com neve
```

A imagem chega como foto no próprio WhatsApp, sem precisar abrir link.

---

## 6. Edição de Imagem

Envie uma foto para a Aisha e ela pergunta o que você quer fazer. Responda com texto ou áudio — não precisa dizer "Aisha", porque ela já sabe que é sobre a imagem.

**Como usar:**
```
[Você envia uma foto]
Aisha: 📷 O que você quer que eu faça com esta imagem?

Você: melhore a qualidade e aumente o brilho
Aisha: ⏳ Processando imagem...
[Aisha envia a imagem melhorada]

Você: agora coloque um filtro vintage
[Aisha envia a imagem com filtro — edição iterativa]
```

**Também funciona por áudio:**
```
[Você envia uma foto]
Aisha: 📷 O que você quer que eu faça com esta imagem?

[áudio] "remove o fundo dessa imagem"
Aisha: ⏳ Processando imagem...
[Aisha envia a imagem sem fundo]
```

**Atalho com legenda:** Se você enviar a foto já com uma legenda no WhatsApp, a legenda é usada como instrução diretamente — a Aisha não pergunta o que fazer.

**Possibilidades:**
- Melhorar qualidade (brilho, contraste, nitidez)
- Mudar estilo (aquarela, desenho, vintage, etc.)
- Remover ou trocar fundo
- Gerar uma nova imagem baseada na original
- Descrever o conteúdo da imagem
- Extrair texto da imagem
- Editar elementos específicos

**Edição iterativa:**
- Após receber a imagem editada, você pode pedir mais modificações na mesma conversa
- A Aisha mantém o contexto e sabe qual imagem está sendo editada

**Observações:**
- A imagem pendente expira após **5 minutos** sem instrução
- Limite de tamanho: 50 MB por imagem

---

## 7. Lembretes

A Aisha agenda lembretes e avisa você com antecedência (padrão: 15 minutos antes). Também envia um link para adicionar o evento ao Google Calendar.

### Criar um lembrete

```
"me lembra da reunião amanhã às 10h com o João"
"Aisha, lembra de comprar remédio hoje às 18h"
"me avisa da consulta médica na sexta às 14h30"
"lembrete: academia todo dia às 7h"
"me lembra de ligar pra mãe toda segunda às 20h"
```

**Resposta da Aisha:**
```
✅ Lembrete criado!
📌 Reunião com João
📅 09/03 às 10:00 (America/Sao_Paulo)
⏰ Aviso: 15 min antes (às 09:45)

🗓️ Adicionar ao Google Calendar:
https://calendar.google.com/calendar/render?...
```

### Listar lembretes

```
"quais são meus lembretes?"
"meus lembretes"
"lista meus lembretes"
```

**Resposta da Aisha:**
```
📋 Seus lembretes:
1. Reunião com João — 09/03 às 10:00
2. Academia — toda segunda às 07:00 🔁
3. Consulta médica — 12/03 às 14:30

Para cancelar: 'cancela o lembrete 1'
```

### Cancelar um lembrete

```
"cancela o lembrete 1"
"apaga o lembrete da reunião"
"remove o lembrete 2"
```

**Resposta da Aisha:**
```
✅ Lembrete cancelado: 'Reunião com João'
```

### Editar um lembrete

```
"muda o lembrete 1 para as 11h"
"altera o lembrete da reunião para sexta às 15h"
"edita o lembrete 2 para amanhã às 8h"
```

**Resposta da Aisha:**
```
✅ Lembrete atualizado!
📌 Reunião com João
📅 09/03 às 11:00
```

### Lembretes recorrentes

```
"me lembra de tomar remédio todo dia às 8h"
"lembrete de academia toda terça e quinta às 7h"
"me avisa toda segunda às 9h para verificar emails"
"lembrete mensal: pagar boleto todo dia 5 às 10h"
```

---

## 8. Roteamento Automático de Modelo

A Aisha escolhe automaticamente o melhor modelo para cada mensagem — você não precisa fazer nada:

| Tipo de mensagem | Modelo usado |
|---|---|
| Saudações, perguntas simples, bate-papo | `gpt-4.1` — rápido e barato |
| Pesquisa, raciocínio, tarefas técnicas | `gpt-5.4` — mais capaz |
| Geração de imagem | `gpt-image-1.5` (via `gpt-5.4`) |
| Edição de imagem (foto do usuário) | `gpt-image-1.5` (via `gpt-5.4` + input multimodal) |
| Transcrição de áudio | `whisper-1` |
| Refinamento de transcrição | `gpt-4o-mini` |
| Extração de intenção de lembrete | `gpt-4o-mini` |

---

## Dicas de uso

**Misturar habilidades funciona:**
```
"Aisha, pesquisa o clima de Fortaleza amanhã e me lembra de levar guarda-chuva às 7h30"
```

**Áudio longo para transcrição:**
- Pode enviar áudios de até vários minutos — o sistema divide automaticamente em partes

**Fuso horário:**
- Os lembretes usam o fuso configurado no servidor (`America/Sao_Paulo` por padrão)
- O horário exibido na confirmação sempre mostra o horário local

**Antecedência do lembrete:**
- O padrão é 15 minutos antes
- Você pode especificar: "me lembra 30 minutos antes da reunião"

**Idioma:**
- A Aisha responde no idioma que você escrever — português, inglês, espanhol, etc.
