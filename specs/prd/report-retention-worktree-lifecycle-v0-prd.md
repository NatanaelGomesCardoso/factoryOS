# PRD — Report Retention & Worktree Lifecycle V0

## Problema

Os reports e worktrees estão crescendo junto com a fábrica, mas ainda falta uma política explícita para classificar o que pode ser arquivado ou limpo no futuro com segurança.

## Objetivo

Criar comandos de planejamento read-only para retenção de reports, lifecycle de worktrees e manutenção combinada.

## Requisitos

- `report-retention-plan`
- `worktree-lifecycle-plan`
- `factory-maintenance-plan`
- indexar reports por tipo;
- classificar worktrees em `active`, `recent_validation`, `stale_candidate`, `protected`, `needs_review`;
- `deleted_files=none`;
- `removed_worktrees=none`.

## Não Objetivos

- remover worktrees;
- mover ou apagar reports;
- alterar branches;
- rodar cleanup automático.
