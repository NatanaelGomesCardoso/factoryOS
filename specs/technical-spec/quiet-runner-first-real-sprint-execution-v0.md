# SPEC Tecnica - Quiet Runner First Real Sprint Execution V0

## Componentes

- `app/codex_quiet_runner.py`
- `app/cli.py`
- `app/execution_evaluator.py`

## Regras do canário

- registrar `git_status_before` e `git_status_after`;
- aceitar `--allowed-path` repetido;
- gerar `changed_files`, `allowed_files`, `disallowed_files` e `changed_files_ok`;
- bloquear quando houver arquivo fora da allowlist;
- preservar compatibilidade com execução anterior sem `--allowed-path`.

## Saídas esperadas

- `changed_files_ok`
- `terminal_ok`
- `captured_log_status`
- `overall_status`
- `no_push`
- `no_deploy`
- `no_paid_api`
- `no_secrets`

## Validação

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m app.cli codex-quiet-run --execute --allowed-path reports/quiet-runner-first-real-sprint/canary.txt ...`
- `TestClient GET / = 200`
- `git diff --check`
