# Desenvolvimento e testes

`make setup` instala os três pacotes Python de forma editável e Chromium. FFmpeg precisa estar no PATH. `make check` executa lint, fronteiras do repositório e testes. CI também compila o site, gera um PDF sintético e constrói a imagem Docker.

O runner `python -m scripts.run_tests` substitui credenciais por valores fictícios, desabilita dotenv e bloqueia conexões externas. Mocks de transporte pertencem aos testes; nenhum teste comum deve chamar Meta, Supabase ou IA reais.

- `tests/unit/agent`: regressões do bot.
- `tests/unit/test_parser.py`: regressões importadas do analisador original.
- `tests/integration/test_playground.py`: equivalência, isolamento, execução offline e recuperação de falhas.
- `tests/fixtures`: somente material sintético com origem documentada.

Para inspecionar PDF: `python -m scripts.check_export_pdf /tmp/aisha-pdf-preview`. Testes `check_export_live` e `check_export_media --live` são opt-in, usam provedores reais e não fazem parte da suíte padrão. Execute-os apenas no ambiente explicitamente escolhido.

Conversas reais ficam em `local/`, nunca em fixtures ou `apps/website/public`. O playground permite `--question`, `--ai`, `--env-file`, `--output` e `--no-pdf`. O modo offline não precisa de nenhuma credencial.
