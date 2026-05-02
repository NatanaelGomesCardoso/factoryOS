# SPEC Tecnica - Token Economy & Output Budget Enforcement V0

## Componentes

- `app/output_budget.py`
- `app/token_usage.py`
- `app/codex_handoff.py`
- `app/factory_start.py`
- `app/cli.py`

## Regras do contrato

- terminal máximo de 35 linhas no uso padrão;
- comandos grandes devem redirecionar stdout para arquivo;
- terminal só deve mostrar métricas compactas e paths de proof/report;
- o prompt do Codex deve carregar o contrato explícito;
- o report do handoff deve registrar as versões do contrato.

## Parser de token usage

O parser deve reconhecer:

- `tokens used`
- `input tokens`
- `cached input tokens`
- `output tokens`
- `total_tokens`
- `input_tokens`
- `output_tokens`
- `cached_input_tokens`

Se houver apenas total, o total deve ser registrado. Se houver detalhado, o detalhado deve ser registrado também.

## Report de budget

`codex-output-budget-report --log <PATH>` deve gravar em `reports/token-economy/<timestamp>.json` e incluir:

- `parser_result`
- `budget_check`
- versão do contrato
- política de stdout

## Validação

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m json.tool specs/sprints/040-token-economy-output-budget-v0.json`
- `python -m app.cli output-budget-contract`
- `python -m app.cli token-usage-parse --log <PATH>`
- `python -m app.cli output-budget-check --log <PATH> --max-lines <N> --max-bytes <N>`
- `python -m app.cli codex-output-budget-report --log <PATH>`

## Fora de escopo

- multi-agent externo;
- live Codex;
- deploy;
- push;
- API paga.
