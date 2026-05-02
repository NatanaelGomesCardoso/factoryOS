# SPEC Tecnica - Captured Log Hard Budget & Truncation V0

## Componentes

- `app/codex_quiet_runner.py`
- `app/output_budget.py`
- `app/token_usage.py`
- `app/cli.py`

## Regras do runner

- separar `terminal_visible_max_lines` e `terminal_visible_max_bytes`;
- separar `captured_log_warning_lines` e `captured_log_warning_bytes`;
- separar `captured_log_hard_lines` e `captured_log_hard_bytes`;
- criar preview truncado seguro quando o log combinado passar `captured_log_truncate_bytes`;
- calcular `sha256` do log completo;
- manter compatibilidade com report antigo.

## Report mínimo

- `terminal_ok`
- `terminal_visible_lines`
- `terminal_visible_bytes`
- `terminal_diff_like_lines`
- `captured_log_status`
- `captured_log_lines`
- `captured_log_bytes`
- `captured_log_diff_like_lines`
- `captured_log_truncated`
- `captured_log_sha256`
- `captured_log_full_path`
- `captured_log_preview_path`
- `overall_status`

## Validação

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m json.tool <report>`

