# Capsule Run Status Normalization V0

## O que é

Normalização local da decisão final de uma execução de cápsula.

## Para que serve

- separar `execution_report`, `export_plan` e `diff_report`;
- transformar `captured_log_status=blocked` em `ok_with_captured_warnings` quando o bloqueio vier só de diff-like lines;
- manter `blocked` quando houver erro real de execução, JSON inválido, `disallowed_files` ou outra evidência de risco;
- produzir um report compacto para consumo pela CLI e pelos gates de sprint.

## Comando

- `capsule-run-status --execution-report <PATH> --export-plan <PATH> --diff-report <PATH>`

