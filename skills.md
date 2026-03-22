# Aisha — Guia de Habilidades

A Aisha é uma assistente pessoal orientada a tarefas. Ela não é um chatbot para bate-papo — seu papel é executar ações concretas para você.

---

## 1. Como funciona

A Aisha analisa cada mensagem e decide o que fazer:

- **Ação clara** → executa diretamente (criar lembrete, pesquisar, resumir, etc.)
- **Pergunta direta** → responde com informação (usa busca na web se necessário)
- **Conteúdo ambíguo** (texto encaminhado, ata, lista, link sem instrução) → pergunta: *"O que você quer que eu faça com isso?"*
- **Pedido impossível** → responde: *"Não tenho essa habilidade."*

**Exemplos:**
```
Você: qual o dólar hoje?
Aisha: [pesquisa e responde]

Você: [encaminha uma ata de reunião]
Aisha: O que você quer que eu faça com isso? Posso resumir, extrair pontos-chave, criar lembretes...

Você: faz uma ligação pra mim
Aisha: Não tenho essa habilidade.
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

**Observações:**
- Áudios longos são divididos automaticamente em partes de 10 minutos e processados em paralelo
- Formatos suportados: OGG, MP3, M4A, WAV, MP4

---

## 3. Chat por Áudio

Envie um áudio **mencionando "Aisha"** para conversar com ela por voz.

**Como usar:**
```
[áudio] "Aisha, qual é a previsão do tempo para amanhã?"
[áudio] "Aisha, me resume esse conceito de machine learning"
[áudio] "Aisha, deixa essa mensagem mais formal: [ditado]"
```

A palavra "Aisha" em qualquer parte do áudio indica que é uma conversa, não uma transcrição.

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

## 7. Documentos (PDF e Word)

Envie um arquivo PDF ou Word (.docx) e a Aisha extrai o texto e gera um resumo. Você também pode dar uma instrução específica junto com o documento.

**Como usar:**
```
[Você envia um PDF]
Aisha: 📄 Processando documento...
Aisha: [resumo estruturado do documento]
```

**Com instrução via legenda:**
```
[Você envia um contrato.pdf com legenda "quais são as cláusulas de rescisão?"]
Aisha: 📄 Processando documento...
Aisha: [resposta focada nas cláusulas de rescisão]
```

**Possibilidades:**
- Resumir contratos, relatórios, artigos, atas
- Extrair informações específicas (datas, valores, nomes)
- Responder perguntas sobre o conteúdo
- Traduzir ou reformatar o conteúdo

**Observações:**
- Formatos suportados: **PDF** e **Word (.docx)**
- PDFs escaneados (só imagem) não são suportados — apenas PDFs com texto digital
- Limite de tamanho: 50 MB por documento

---

## 8. Lembretes

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

## 9. Tarefas Agendadas (Scheduled Tasks)

A Aisha executa tarefas recorrentes automaticamente: pesquisa na web, gera um relatório com IA e envia o resultado no WhatsApp. Diferente dos lembretes (que enviam um texto fixo), as tarefas agendadas **executam uma ação do agente** a cada disparo.

### Criar uma tarefa agendada

```
"toda segunda me mande um relatório com as últimas notícias sobre o Irã"
"todo dia às 7h me mande o resumo do mercado financeiro"
"toda sexta às 18h pesquise as novidades de IA da semana e me mande um resumo"
"diariamente às 8h me mande a previsão do tempo para Fortaleza"
```

**Resposta da Aisha:**
```
✅ Tarefa agendada criada!
📌 Relatório Irã
🕐 toda segunda-feira às 09:00
📝 Pesquise as últimas notícias sobre o Irã da última semana...

Cada vez que disparar, vou executar essa tarefa com busca na web e te enviar o resultado.
```

### Listar tarefas agendadas

```
"quais são minhas tarefas agendadas?"
"lista minhas tarefas recorrentes"
```

### Cancelar uma tarefa agendada

```
"cancela a tarefa agendada 1"
"remove a tarefa recorrente do relatório"
```

**Observações:**
- Cada execução usa busca na web para informações atualizadas
- O modelo GPT-5.4 gera o relatório — mesma qualidade de uma conversa complexa
- Tarefas sobrevivem reinicializações do servidor (persistidas no banco)

---

## 10. Análise de Vídeos do YouTube

A Aisha analisa qualquer vídeo público do YouTube usando o Gemini 2.5 Flash. Basta enviar o link.

### Enviar link com instrução (processa imediatamente)

```
https://youtu.be/dQw4w9WgXcQ faz um resumo
https://www.youtube.com/watch?v=abc123 transcreve esse vídeo
https://youtu.be/xyz quais são os pontos principais?
```

### Enviar só o link (Aisha pergunta o que fazer)

```
Você: https://youtu.be/dQw4w9WgXcQ
Aisha: 🎬 Link do YouTube detectado! O que você quer que eu faça com esse vídeo?

Você: resume em tópicos
Aisha: [análise completa do vídeo]
```

**Exemplos de instruções:**
```
"resume"
"transcreve"
"quais os pontos principais?"
"explica os conceitos técnicos mencionados"
"faz um post para o LinkedIn baseado nesse vídeo"
"isso é adequado para crianças?"
"quais os timestamps mais importantes?"
```

**Observações:**
- O link pendente expira após **10 minutos** sem instrução
- Funciona apenas com vídeos públicos

---

## 11. Leitura de Páginas Web

A Aisha lê qualquer URL pública e processa o conteúdo conforme sua instrução. Basta enviar o link.

### Enviar link com instrução (processa imediatamente)

```
https://g1.globo.com/noticia resume essa notícia
https://www.bbc.com/news/article-123 traduz para português
https://blog.exemplo.com/post quais são os pontos principais?
```

### Enviar só o link (Aisha pergunta o que fazer)

```
Você: https://g1.globo.com/noticia
Aisha: 🔗 Link detectado! O que você quer que eu faça com essa página?

Você: resume em tópicos
Aisha: [resumo da notícia]
```

**Exemplos de instruções:**
```
"resume"
"traduz para inglês"
"quais os pontos principais?"
"explica de forma simples"
"extrai os dados mencionados"
"faz um post para LinkedIn baseado nisso"
"quem escreveu e quando foi publicado?"
```

**Observações:**
- O link pendente expira após **10 minutos** sem instrução
- Funciona com artigos, notícias, blogs, documentações e qualquer página com conteúdo textual público
- Páginas que exigem login ou têm conteúdo gerado por JavaScript podem não funcionar

---

## 12. Personalização e Perfil

A Aisha aprende sobre você e se adapta. Você pode definir um contexto pessoal, mudar o idioma da conversa, e consultar o que ela sabe sobre você.

### Contexto pessoal

Envie informações sobre você — a Aisha vai lembrar para sempre e usar em todas as conversas.

```
"Sou programador, trabalho com Python e moro em Fortaleza"
"Meu nome é Rodrigo, gosto de tecnologia e café"
"Quero que você seja mais direta e use menos emojis"
"Sou estudante de engenharia, me ajuda com termos técnicos"
```

Você pode atualizar seu contexto a qualquer momento — basta enviar novas informações.

### Mudar o idioma

```
"Vamos falar em inglês"
"Podemos conversar em espanhol?"
"Switch to English"
```

A Aisha vai responder no idioma escolhido dali em diante.

### O que você sabe de mim?

```
"O que você sabe sobre mim?"
"Me diga tudo que sabe de mim"
"Qual é meu perfil?"
```

A Aisha lista: contexto pessoal salvo, idioma preferido, lembretes ativos e estatísticas de uso (quantos áudios, imagens, documentos e vídeos você já processou).

---

## 13. Download de Vídeo

Envie um link do YouTube ou X/Twitter junto com uma palavra de download e a Aisha gera um link temporário para você baixar o vídeo.

**Como usar:**
```
"baixa esse vídeo: https://youtu.be/xxxx"
"https://x.com/user/status/123 me manda esse vídeo"
"download: https://www.youtube.com/watch?v=xxxx"

[após enviar um link do YouTube sem instrução]
Aisha: 🎬 Link do YouTube detectado! O que você quer...
Você: baixa o vídeo
```

**Funciona com:**
- YouTube (`youtube.com`, `youtu.be`)
- X/Twitter (`x.com`, `twitter.com`)

**Sobre o link de download:**
- É um link temporário que expira em **30 minutos**
- Resolução máxima: 720p (para manter o arquivo menor)
- Funciona apenas enquanto o servidor estiver rodando

**Palavras que ativam o download:**
`baixa`, `baixar`, `download`, `salva`, `salvar`, `me manda`, `manda`, `pega`

**Limitações:**
- Vídeos protegidos ou privados não podem ser baixados
- X/Twitter pode falhar em tweets específicos com proteção da plataforma

---

## 14. Roteamento Automático de Modelo

A Aisha escolhe automaticamente o melhor modelo para cada tarefa — você não precisa fazer nada:

| Tipo de tarefa | Modelo usado |
|---|---|
| Orquestração geral (agente) | `gpt-5.4` — decide quais ferramentas usar |
| Pesquisa, raciocínio, tarefas complexas | `gpt-5.4` — mais capaz |
| Geração e edição de imagem | `gpt-5.4` + ferramenta `image_generation` |
| Transcrição de áudio | `whisper-1` |
| Refinamento de transcrição | `gpt-4o-mini` |
| Extração de intenção de lembrete | `gpt-4.1-mini` |
| Extração de intenção de tarefa agendada | `gpt-4o-mini` |
| Execução de tarefa agendada (com web search) | `gpt-5.4` |
| Resumo de documentos PDF/DOCX | `gpt-4.1` |
| Análise de vídeo YouTube | `gemini-2.5-flash` |
| Leitura de páginas web | Jina Reader + `gpt-4.1` |

---

## Dicas de uso

**Misturar habilidades funciona:**
```
"Aisha, pesquisa o clima de Fortaleza amanhã e me lembra de levar guarda-chuva às 7h30"
```

**Áudio longo para transcrição:**
- Pode enviar áudios de até vários minutos — o sistema divide automaticamente em partes de 10 minutos

**Fuso horário:**
- Os lembretes usam o fuso configurado no servidor (`America/Sao_Paulo` por padrão)
- O horário exibido na confirmação sempre mostra o horário local

**Antecedência do lembrete:**
- O padrão é 15 minutos antes
- Você pode especificar: "me lembra 30 minutos antes da reunião"

**Idioma:**
- A Aisha responde no idioma que você escrever — português, inglês, espanhol, etc.
- Você pode definir um idioma fixo com "vamos falar em inglês" — a preferência fica salva
