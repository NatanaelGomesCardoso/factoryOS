# SPEC Tecnica - Quiet Runner Budget Calibration V0

## Componentes

- `app/codex_quiet_runner.py`
- `app/compact_execution_harness.py`
- `app/cli.py`

## Regras do runner

- separar `terminal_visible_budget` de `captured_log_budget`;
- `terminal_ok` depende apenas do que o terminal visível mostra;
- `captured_log_status` pode ser `ok`, `warn` ou `blocked`;
- diff-like lines capturadas viram warning quando abaixo do limite forte;
- `ok=true` exige saída 0, terminal compacta e segurança sem violações.

## Report mínimo

- `terminal_ok`
- `terminal_visible_lines`
- `terminal_visible_bytes`
- `terminal_diff_like_lines`
- `captured_log_status`
- `captured_log_warnings`
- `overall_status`

## Validação

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m app.cli codex-quiet-run --dry-run`
- `python -m app.cli compact-exec-check --mode terminal --log <PATH> --category code_small`
- `python -m app.cli compact-exec-check --mode captured --log <PATH> --category code_small`
