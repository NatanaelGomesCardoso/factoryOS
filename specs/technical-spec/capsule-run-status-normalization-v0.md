# Technical Spec - Capsule Run Status Normalization V0

## Componentes

- `app/codex_capsule_execution.py`
- `app/cli.py`

## Comando

- `capsule-run-status --execution-report <PATH> --export-plan <PATH> --diff-report <PATH>`

## Regra principal

- `exit_code=0`, `export_plan ok=true`, `disallowed_files=[]` e bloqueio apenas por diff-like lines capturadas => `ok_with_captured_warnings`.

