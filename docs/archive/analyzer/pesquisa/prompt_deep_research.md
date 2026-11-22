# Prompt de deep research: analisadores de conversa e o mercado jurídico brasileiro

Cole o bloco abaixo numa ferramenta de pesquisa profunda (ChatGPT Deep Research, Gemini Deep Research, Perplexity, Claude Research). Os resultados voltam para `docs/pesquisa/`.

---

## Contexto

Estou construindo uma ferramenta que transforma a exportação de uma conversa de WhatsApp (texto, áudios, imagens, PDFs, vídeos) num dossiê que humanos e IAs conseguem ler. O protótipo já funciona e entrega quatro níveis:

- **Nível 0:** conversa legível, com mídia no lugar e um id citável por mensagem.
- **Nível 1:** transcrição fiel dos áudios, sem reescrever o texto.
- **Nível 2:** comentário de cada mídia, escrito com o contexto da conversa.
- **Nível 3:** resumo, linha do tempo, valores, compromissos e pendências, com cada afirmação apontando a mensagem de origem.

Num caso real, com 398 mensagens e 22 minutos de áudio, o processamento completo custou US$ 0,66 de API e levou 39 segundos.

A hipótese principal é vender para advogados brasileiros, que recebem de clientes conversas longas de WhatsApp, com muito áudio, e precisam entender, organizar e citar esse material. O produto não autentica a prova. A ideia é complementar quem faz isso, como Verifact e ata notarial, e não competir com eles.

O que já sei, e você deve verificar em vez de presumir:

- O chatview.ai cobra por chat, sem assinatura: US$ 4,99 por um PDF simples, US$ 14,99 por um pacote de evidências, US$ 19,99 com resumo de IA e US$ 19,99 por um passe de 30 dias. Processa tudo no navegador, não transcreve áudio e é voltado aos EUA (usa numeração Bates).
- Encontrei outros exportadores e conversores: getchatexport, paperthread, preserve.chat, messagetopdf, wholething.
- No Brasil, o STJ exige cadeia de custódia e perícia quando há dúvida razoável sobre prova digital (por exemplo, HC 828.054 e uma decisão da 6ª Turma em março de 2026). A ata notarial (art. 384 do CPC) e a captura técnica do Verifact são aceitas, e o TJSP já reconheceu o Verifact como substituto da ata.
- A Meta proíbe, desde 15/01/2026, chatbots de IA de uso geral na API do WhatsApp Business. Números brasileiros (+55) foram excetuados por ordem do CADE.

## Perguntas

### 1. Panorama global de analisadores e exportadores de conversa
- Quem existe hoje: WhatsApp, Telegram, iMessage, Signal, e-mail, Slack? Separe em visualizador ou exportador, transformador em PDF, pacote de evidências, análise com IA e ferramenta forense (como Cellebrite, Magnet, Oxygen).
- Para cada player relevante, quero: público, funcionalidades, se transcreve áudio, se usa IA, onde processa (navegador, servidor ou celular), preço e modelo de cobrança, canal de aquisição e sinais de tração (tráfego, avaliações, investimento, notícias).
- Que padrões de modelo de negócio funcionam: cobrança por chat, passe por caso, assinatura, por página, B2B/API ou white label? Há evidências de receita ou de conversão?

### 2. O mercado jurídico brasileiro
- Como advogados brasileiros lidam hoje com WhatsApp de clientes nas áreas trabalhista, família, consumidor, cível e criminal? Que ferramentas usam e quanto tempo isso consome?
- Que serviços brasileiros já atendem preservação, autenticação ou organização de conversas, e quanto cobram? Verifique pelo menos: Verifact, OriginalMy/PACWeb, ata notarial presencial e pelo e-Notariado, peritos digitais e cartórios. Quanto custa uma ata notarial de conversa em alguns estados?
- Legaltechs brasileiras com IA para documentos e prova (ferramentas de petição, jurimetria, IA jurídica): alguma já transcreve ou analisa WhatsApp? Quem seria concorrente e quem seria parceiro?
- Qual o tamanho do mercado? Número de advogados ativos (OAB), escritórios por porte e gasto com software jurídico. Use dados com fonte e data.

### 3. Requisitos legais e regulatórios para o produto
- Jurisprudência atual (2024–2026) sobre o uso de conversas e áudios de WhatsApp como prova no cível, no trabalhista e no penal: o que os tribunais aceitam, o que rejeitam e por quê. Inclua os arts. 369, 384 e 422 do CPC, os arts. 158-A a 158-F do CPP e a norma técnica da ABNT citada pelo STJ.
- Transcrição de áudio feita por IA anexada a um processo: há decisões ou orientações sobre isso? Exige-se transcrição por perito?
- LGPD: qual a base legal para um advogado enviar a conversa do cliente, com dados de terceiros, a um processador que usa API de IA fora do Brasil? O que precisa constar em contrato, política de privacidade e transferência internacional de dados?
- OAB e CNJ: que regras ou recomendações sobre uso de IA generativa por advogados estão em vigor (Conselho Federal da OAB, seccionais, resoluções do CNJ)? Algo impede ou condiciona uma ferramenta como esta?
- Que afirmações de marketing seriam arriscadas, como "validade jurídica" ou "prova aceita em juízo", à luz do CDC e do Código de Ética da OAB?

### 4. O que poderia funcionar no Brasil
- Proposta de valor mais forte para o advogado: economizar tempo de leitura, montar a linha do tempo dos fatos, extrair valores e compromissos, preparar a petição ou entregar um anexo organizado ao juiz?
- Preço plausível em reais e forma de cobrança: por caso, por pacote de casos ou por assinatura do escritório? Compare com o que os advogados já pagam por ata notarial, Verifact e softwares jurídicos.
- Canais de aquisição que funcionam com advogados brasileiros: SEO, Instagram jurídico, OAB e seccionais, AB2L, parcerias com cartórios, com o Verifact ou com softwares de gestão jurídica.
- Formato de entrega: web com upload do zip, integração com softwares jurídicos, API para parceiros ou WhatsApp (considerando a regra da Meta).
- Riscos que podem matar o produto: técnicos (limites da exportação do WhatsApp), legais, de confiança (alucinação da IA) e competitivos (o Verifact ou uma legaltech grande lançarem o mesmo recurso).

## Formato da resposta

1. Um resumo executivo de uma página com as 5 conclusões que mais mudam a decisão de construir ou não, cada uma com o nível de confiança.
2. Tabelas comparativas de concorrentes globais e brasileiros: nome, público, funcionalidades, transcreve áudio, usa IA, preço, modelo de cobrança e fonte.
3. Uma seção jurídica com decisões citadas pelo número do processo, tribunal e data, separando o que é jurisprudência consolidada do que são casos isolados.
4. Uma recomendação de posicionamento, preço e canal para um produto mínimo no Brasil, com os três experimentos mais baratos para validar antes de investir.
5. Uma lista do que você não conseguiu confirmar.

Regras:
- Cite a fonte e a data de cada fato. Prefira fontes primárias: site oficial, tribunal, OAB, CNJ, Diário Oficial.
- Pesquise em português e em inglês.
- Marque como estimativa tudo o que não tiver fonte. Não invente preços, números de processo ou nomes de empresas.
- Dê prioridade a informação de 2025 e 2026.
