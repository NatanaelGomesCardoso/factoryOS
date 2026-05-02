# SPEC Tecnica - Codex CLI Output Suppression & Quiet Runner V0

## Componentes

- `app/codex_quiet_runner.py`
- `app/token_usage.py`
- `app/output_budget.py`
- `app/cli.py`

## Regras do runner

- montar comando com `--ignore-user-config` e `--ephemeral`;
- usar `--cd` com o diretório alvo;
- aceitar `--prompt-file`, `--cwd`, `--model`, `--reasoning`, `--sandbox`, `--approval`, `--label`;
- aceitar `--allowed-path` e flags de segurança opcionais;
- dry-run não executa Codex;
- execute exige `FACTORYOS_ENABLE_QUIET_CODEX=1`;
- stdout, stderr e combined log devem ir para arquivo;
- resumo terminal máximo de 20 linhas.

## Métricas

- `tokens_used`
- `input_tokens`
- `cached_input_tokens`
- `output_tokens`
- `output_lines`
- `output_bytes`
- `diff_like_lines`

## Report mínimo

- `ok`
- `quiet_runner_version`
- `executed`
- `command_contains_ignore_user_config`
- `command_contains_ephemeral`
- `stdout_log_path`
- `stderr_log_path`
- `combined_log_path`
- `token_usage`
- `output_budget_check`
- `diff_like_lines`
- `diff_suppressed`
- `terminal_ok`
- `captured_log_status`
- `overall_status`

## Validação

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m app.cli codex-quiet-run --dry-run`
- `python -m app.cli codex-quiet-ab-report`
