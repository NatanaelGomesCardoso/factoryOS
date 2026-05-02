# Token Economy

Este documento registra o contrato local do FactoryOS para reduzir custo operacional de output e de stdout.

## Princípios

- Terminal curto por padrão.
- Saídas grandes vão para `<TMP_DIR>` ou `reports/`.
- `task-list`, `run-list` e reports grandes não devem ser colados em prompt.
- O backend deve produzir handoff compacto e evidência detalhada em arquivos.

## Contrato de saída

- `Terminal max 35 lines.`
- `No full diffs.`
- `No full worktree list.`
- `No full task-list/run-list JSON.`
- `No full reports list.`
- `Redirect large command output to files in <TMP_DIR> or reports.`
- `Print only compact metrics and report paths.`
- `Write detailed evidence to reports/proofs.`
- `Final answer must be COMPACT FINAL SUMMARY only.`

## Ferramentas

- `output-budget-contract`
- `token-usage-parse --log <PATH>`
- `output-budget-check --log <PATH> --max-lines <N> --max-bytes <N>`
- `codex-output-budget-report --log <PATH>`

## Uso esperado

- Handoff e prompts do Codex devem carregar o contrato.
- Reports devem registrar versão do contrato, policy de stdout e disponibilidade do parser.
- Logs de tokens devem ser resumidos localmente antes de virar contexto maior.
