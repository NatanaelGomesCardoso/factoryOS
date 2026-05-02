# Technical Spec — Capsule Execution & Patch Gate V0

## Visão geral

A cápsula é executada por Codex com quiet runner, e o resultado passa por diff e export-plan antes de qualquer aplicação.

## Componentes

- `app/codex_capsule_execution.py`
- `app/codex_context_capsule.py`
- `app/codex_quiet_runner.py`
- `app/cli.py`

## Comandos

### `codex-capsule-run`

- usa `codex-quiet-run` com `cwd` na cápsula;
- registra tokens, output_lines e output_bytes;
- gera report em `reports/capsule-executions/`.

### `codex-capsule-diff`

- salva o diff em arquivo;
- imprime somente contadores e caminhos;
- reporta `changed_files`, `changed_files_count`, `diff_path` e `diff_bytes`.

### `codex-capsule-export-plan`

- compara cápsula com `source_root`;
- permite apenas `included_files` do manifest;
- bloqueia escrita automática;
- produz plano para revisão local.

### `codex-capsule-apply`

- existe somente em dry-run nesta sprint;
- não aplica ao repo real.

## Gate

- o canário deve mostrar economia de tokens;
- arquivos extras não podem entrar no plano de exportação;
- não imprimir patch bruto no terminal.

