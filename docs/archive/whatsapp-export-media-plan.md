# Plano aprovado — mídias no PDF (14/11/2026)

Uso pessoal mínimo; executar no serviço atual, sem worker externo. Acrescentar
transcrições fiéis (sem refinamento), imagens numeradas com descrição visual,
comentários seletivos com referências e guias separados para humanos e IA.
Preservar IDs msg-...; documentos apenas pelo nome e momento de envio.

Limites: ZIP 50 MiB; texto 2 MiB / 100 mil caracteres; 60 minutos e 200 áudios;
40 imagens de até 10 MiB / 20 MP; mídias lidas até 250 MiB; contexto enriquecido
200 mil caracteres; processamento 15 minutos; PDF 20 MiB / 60 segundos.
Uma exportação com mídia por processo, até duas chamadas de mídia simultâneas.

Áudios/ZIP temporários apenas durante processamento. Transcrições/resultados e
cópias reduzidas privadas de imagens duram até a expiração da conversa (24h).
Reenvio reutiliza resultados; reinício pode exigir ZIP para áudios pendentes.
Limpeza na inicialização e a cada 15 minutos; esquecer apaga imagens e registro.
Payload v3 compatível com v1/v2, atualizações condicionais para impedir gravações
atrasadas após substituição ou exclusão. Falhas individuais geram PDF com ressalvas.

Testes sintéticos de ingestão, limites, referências, isolamento, retries, limpeza,
retenção e regressão; PDF renderizado e inspecionado visualmente. Commits separados,
nenhuma alteração local anterior incluída; validar container e serviços reais antes
de ativar WHATSAPP_EXPORT_MEDIA_ENABLED. Manter rollback para PDF apenas de texto.
