# Technical Spec — Minimal Codex Context Capsule V0

## Visão geral

A implementação cria uma cápsula Git autocontida com um subconjunto explícito de arquivos do `source_root`.

## Componentes

- `app/codex_context_capsule.py`
- `app/cli.py`
- `docs/codex-context-capsule.md`
- `specs/sprints/048-minimal-codex-context-capsule-v0.json`

## Comandos

### `codex-capsule-create`

- `--label <LABEL>`
- `--source-root <PATH>`
- `--include <PATH>` repetível
- `--use-latest-digest`
- `--max-context-bytes <N>`

Comportamento:

- cria a cápsula em `workspaces/codex-capsules/<timestamp>-<label>/`;
- inicializa Git;
- escreve `AGENTS.md` mínimo;
- copia apenas os includes;
- copia digest recente se houver;
- grava `CAPSULE_MANIFEST.json`;
- grava report em `reports/codex-context-capsules/`.

### `codex-capsule-list`

- lista cápsulas recentes com tamanho e flags de integridade.

### `codex-capsule-inspect`

- devolve `files_count`, `total_bytes`, `has_git`, `has_agents`, `has_manifest`, `excluded_patterns` e `ok`.

## Gate

- o total final deve respeitar `max_context_bytes`;
- segredos e reports grandes são bloqueados;
- a cápsula deve permanecer como Git repo.

