# Compact Execution Harness

## Para que serve

Padronizar budgets compactos por categoria e decidir se um log ou execução ficou pequeno o bastante para o fluxo FactoryOS.

## Categorias

- `docs_only`
- `code_small`
- `code_medium`
- `live_canary`
- `security_review`
- `factory_start`

## Campos do budget

- `max_terminal_lines`
- `max_output_bytes`
- `max_diff_like_lines_terminal`
- `preferred_runner`
- `model_hint`
- `reasoning_hint`

## Regras

- `compact-exec-check` aceita `--mode terminal` e `--mode captured`.
- `terminal` continua bloqueando diff-like lines.
- `captured` trata diff-like lines como warning quando o restante fica dentro do budget.
- `compact-exec-report` grava prova em `reports/compact-execution/`.
- O handoff deve recomendar `codex-quiet-run` por padrão.
- `raw_codex_exec_allowed` só deve ficar `true` em revisão manual explícita.

## Uso recomendado

- `codex-quiet-run` para canários pequenos.
- `compact-exec-check` para validar logs antes de anexar em reports.
- `compact-exec-report` para consolidar evidência curta.
