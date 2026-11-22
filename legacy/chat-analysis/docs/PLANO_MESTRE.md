# Plano Mestre — Dossiê de Conversas de WhatsApp

> Documento de referência do projeto. Mantenha-o atualizado quando decisões mudarem.
> O andamento do dia a dia fica em [DIARIO.md](DIARIO.md).

## O que é o projeto

Uma ferramenta que transforma a exportação de uma conversa de WhatsApp (texto + áudios + imagens + PDFs + vídeos) em um **dossiê compreensível**, para dois consumidores:

- **Uma IA** (ChatGPT, Claude): Markdown com transcrições fiéis, descrições de mídia com contexto e citações por mensagem, para analisar a conversa sem perder o sentido das mídias.
- **Um humano** (futuramente): versão legível/PDF.

### Princípios já decididos

1. **Dado bruto intocado**: transcrições nunca são "corrigidas" por LLM; contexto entra como camada separada de anotação.
2. **Processamento iterativo e cronológico**: cada mídia é interpretada com o contexto acumulado (incluindo transcrições anteriores) e algumas mensagens posteriores.
3. **Conteúdo pesado vira ficha com link** (`anexos/doc-NNN.md`): um livro em PDF nunca entra inteiro no dossiê.
4. **Núcleo separado do canal**: o motor (ler → transcrever → descrever → gerar dossiê) não depende de como o cliente consome (CLI, web, WhatsApp).

### Hipótese de negócio (a validar, não decidida)

Mercado mais promissor: **advogados** que recebem de clientes conversas longas de WhatsApp com muito áudio. Arquitetos e corretores ficam como mercado secundário.

**Posicionamento revisado após a pesquisa de 31/10/2026: dossiê citável, não "IA que lê WhatsApp".** Transcrever áudio e montar linha do tempo já é recurso do Jus IA (Jusbrasil) e do Jusfy, que vendem assinatura para advogados. O que eles não fazem, pelo que está publicado:

- receber a exportação inteira (zip com centenas de mensagens e dezenas de áudios). O Jus IA recebe um arquivo por vez, áudios de até 5 minutos, compartilhados do celular;
- mostrar cada mídia na posição original da conversa;
- dar um id estável por mensagem e fazer cada afirmação da IA apontar para a mensagem de origem;
- separar o texto fiel da interpretação.

Frase de posicionamento sugerida pela pesquisa: "Transforme a exportação do WhatsApp em um dossiê navegável e citável para o caso". A palavra que vende é **citável**, não "inteligente".

Complemento de quem autentica, não concorrente: Verifact, PACWeb, ata notarial e perito fazem a prova; nós organizamos e tornamos o material revisável. O Verifact é candidato a parceiro.

Concorrentes e referências: chatview.ai (EUA, US$ 5–20 por chat, sem transcrição de áudio), Jus IA (R$ 78,90–208,90/mês), Jusfy (R$ 77–227/mês). Detalhes e fontes em [pesquisa/deep-research-report.md](pesquisa/deep-research-report.md).

### Restrições conhecidas

- **Exportação corta histórico**: ajuda antiga do WhatsApp falava em ~10k mensagens com mídia / 40k sem; mídias só as recentes. WhatsApp Web/Windows permite intervalo de datas mas sem mídia.
- **Bot no WhatsApp**: a Meta proibiu IA de uso geral na API Business a partir de 15/01/2026. O CADE suspendeu essas regras no mercado brasileiro, decisão mantida em 04/03/2026 e reforçada em abril com multa diária. A versão "números +55 excetuados" não foi confirmada em fonte oficial. Situação instável: não depender disso. Upload do zip pela web é o canal.
- **LGPD**: o advogado pode usar como base legal o exercício regular de direitos em processo (art. 7), mas dados sensíveis seguem o art. 11. Enviar para API fora do Brasil exige mecanismo de transferência internacional (Resolução ANPD 19/2024, cláusulas-padrão), contrato com o processador, lista de suboperadores e aviso de privacidade em português.
- **OAB**: Recomendação 001/2024 e Resolução 16/2026 exigem supervisão do advogado, sigilo, proteção de dados e publicidade que não insinue substituir o advogado nem aprovação da OAB. Vender para o advogado, não para o cliente final.
- **Prova judicial**: não há regra geral de que print de WhatsApp sem ata notarial seja inválido, nem de que baste sempre. O STJ distingue coleta pela polícia (rigor técnico) de coleta pelo particular confirmada em juízo. O hash do zip só prova que a nossa cópia não mudou, não que a conversa é autêntica. O TJSP aceitou relatórios do Verifact em casos individuais; dizer que "substitui a ata notarial" é exagero. **Não prometer validade jurídica.**
- **Transcrição por IA**: o STJ (HC 1.059.475/SP, abr/2026) excluiu um laudo de IA usado para contrariar perícia acústica oficial. Não há regra exigindo perito para uma transcrição de conveniência com o áudio original anexado. Rotular como "transcrição automática para conveniência; o áudio original prevalece".

### Histórico

- O projeto começou como fork do [whatsapp-chat-viewer](https://github.com/rodrigodesalvobraz/whatsapp-chat-viewer) (MIT), mas o clone foi abandonado em 31/10/2026: parser só lia formato Android, saída era HTML, processamento de mídia em silos sem contexto acumulado. Ideias aproveitadas: id estável por mensagem (hash) e estrutura de prompts com contexto.

## As fases do projeto

```mermaid
flowchart LR
  f0[Fase 0: Material de teste] --> f1[Fase 1: Teste tecnico / dossie v1]
  f1 --> f2[Fase 2: Validacao com usuarios]
  f2 --> decisao{Dossie ajuda e alguem pagaria?}
  decisao -->|sim| f3[Fase 3: Produto minimo lancavel]
  decisao -->|nao| pivo[Pivotar ou parar barato]
  f3 --> f4[Fase 4: Iterar e escalar]
```

### Fase 0 — Material de teste (usuário)

Exportar 2–3 conversas reais difíceis para `data/` (fora do Git): iPhone com mídia (já existe: corretora de planos, 610 msgs, 22/set–31/out/2026, 145 mídias citadas / 35 presentes), idealmente uma de Android e um grupo. Garantir `OPENAI_API_KEY` no ambiente.

### Fase 1 — Teste técnico (1–2 semanas) ← ESTAMOS AQUI

Construir o motor do zero e responder com evidência:

1. Lemos 100% das exportações reais (iPhone e Android)?
2. Transcrição de áudio em português é boa o suficiente?
3. Descrições com contexto ficam úteis?
4. Custo e tempo por conversa (600 msgs; extrapolar para 5k)?
5. **O dossiê responde perguntas melhor que o `.txt` bruto colado no ChatGPT?** (teste com ~10 perguntas de resposta conhecida)

Detalhamento em [PLANO_FASE1.md](PLANO_FASE1.md).

### Fase 2 — Validação (em paralelo ao fim da Fase 1)

Com o dossiê real em mãos (nunca slides):

- 3–5 advogados (trabalhista, família, consumidor): como lidam hoje com WhatsApp de clientes? O que falta no dossiê? Pagariam R$ 50–150/caso? Como prefeririam receber?
- O amigo arquiteto: dossiê de decisões de projeto resolve a dor dele?
- Contato com Verifact (só com demo pronta; mostrar resultado, não método).

### Fase 3 — Produto mínimo lançável (só se Fase 2 validar)

Decidir com evidência as três perguntas abertas:

1. **O que o produto faz**: recorte exato (dossiê genérico? perfil jurídico? decisões de projeto?).
2. **Como o cliente consome**: página web com upload do zip é o caminho provável (bot WhatsApp descartado por ora).
3. **Monetização**: referência chatview = pagamento avulso por chat, sem assinatura; precificar após medir custo real de API na Fase 1.

Lançar mínimo: página + upload + processamento + entrega + pagamento (Pix). Iterar (lançar, testar, iterar).

### Fase 4 — Iterar e escalar

Guiado por uso real. Possibilidades já mapeadas: versão PDF para humanos, vídeo (ffmpeg + visão), resumos em camadas para chats de anos, perfis por nicho, parceria Verifact.
