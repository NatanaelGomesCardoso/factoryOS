# SPEC Tecnica - Compact Execution Harness V0

## Componentes

- `app/compact_execution_harness.py`
- `app/codex_quiet_runner.py`
- `app/codex_handoff.py`
- `app/factory_start.py`
- `app/cli.py`

## Categorias

- `docs_only`
- `code_small`
- `code_medium`
- `live_canary`
- `security_review`
- `factory_start`

## Regras

- cada categoria tem budget de linhas e bytes;
- `compact-exec-check --mode terminal` deve bloquear output que pareça patch;
- `compact-exec-check --mode captured` deve transformar diff-like lines em warning quando o restante estiver dentro do budget;
- `preferred_runner` padrão é `codex-quiet-run`;
- report deve consolidar budget, check e recomendações;
- handoff deve carregar `quiet_runner_recommended=true` e `diff_suppression_required=true`.

## Report

- `compact_execution_harness_version`
- `category`
- `mode`
- `budget`
- `check`
- `log_path`
- `report_path`

## Validação

- `python -m app.cli compact-exec-budget`
- `python -m app.cli compact-exec-check --log <PATH> --category code_small`
- `python -m app.cli compact-exec-report --log <PATH> --category code_small`
