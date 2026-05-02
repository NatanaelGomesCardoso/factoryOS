# Reuse First - Capsule Run Status Normalization V0

## Ideia

Antes de criar novos gates de execução, reutilizar os reports de cápsula, export-plan e diff para normalizar o status final.

## Reuso

- `app/codex_capsule_execution.py`
- `app/codex_quiet_runner.py`
- `reports/capsule-executions/`
- `reports/capsule-export-plans/`
- `reports/capsule-diffs/`

## Resultado esperado

- `captured_log_status=blocked` por diff-like lines vira `ok_with_captured_warnings` quando a execução terminou com `exit_code=0`;
- `disallowed_files` continua bloqueando;
- JSON inválido continua bloqueando.

