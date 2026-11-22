# Testes unitários da Aisha

Esta pasta concentra os testes da lógica da Aisha. APIs, banco de dados,
scheduler, relógio, filesystem e subprocessos são simulados: a suíte não deve
fazer chamadas externas nem exigir credenciais reais.

## Estrutura

- `skills/`: regras de negócio, persistência e estados pendentes.
- `tools/`: contratos das ferramentas expostas ao agente.
- `test_agent.py`: loop agentic e interpretação das respostas.
- `test_app_*.py`: segurança, webhook e handlers.
- `_helpers.py`: ambiente e fakes compartilhados.
- `RESULTS.md`: último resultado completo registrado.

## Como executar

Na raiz do repositório:

```bash
source .venv/bin/activate  # somente se .venv existir
python -m unittest discover -s tests -v
```

Somente esta suíte:

```bash
python -m unittest discover -s tests/aisha_unit -t . -v
```

Os testes usam apenas `unittest` e `unittest.mock`, sem dependências adicionais.
