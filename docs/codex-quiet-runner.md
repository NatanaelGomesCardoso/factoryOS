# Codex Quiet Runner

## Para que serve

Executar `codex exec` sem despejar stdout, stderr, diff ou patch no terminal.

## Regras

- Capturar stdout, stderr e combined log em arquivo.
- Imprimir apenas resumo curto.
- Registrar uso de tokens quando disponível.
- Separar `terminal_visible_budget`, `captured_log_warning_budget`, `captured_log_hard_limit` e `captured_log_truncation_policy`.
- Marcar `captured_log_status` como `ok`, `warn` ou `blocked`.
- Bloquear quando o limite duro for ultrapassado ou houver violação de segurança.
- Criar preview truncado seguro quando o log combinado passar o limite de truncation.
- Nunca exibir patch bruto no terminal.

## Comandos

- `codex-quiet-run --prompt-file <PATH> --cwd <PATH> --model <MODEL> --reasoning <LOW|MEDIUM> --sandbox <MODE> --approval <POLICY> --label <LABEL> [--allowed-path <PATH>] [--no-push] [--no-deploy] [--no-paid-api] [--no-secrets] --dry-run`
- `codex-quiet-run ... --execute`
- `codex-quiet-ab-report --log-a <PATH> --log-b <PATH>`

## Saídas

- report em `reports/codex-quiet-runs/`
- logs em `reports/codex-quiet-runs/`
- preview seguro truncado quando necessário
- resumo terminal compacto, sempre abaixo de 20 linhas
- report inclui `terminal_ok`, `captured_log_status`, `captured_log_truncated`, `captured_log_sha256`, `captured_log_full_path`, `captured_log_preview_path`, `overall_status` e `changed_files` quando aplicável

## Segurança

- `--execute` exige `FACTORYOS_ENABLE_QUIET_CODEX=1`
- sem segredos em prompt, log ou report
- sem `shell=True`
