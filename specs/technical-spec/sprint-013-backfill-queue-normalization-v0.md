# SPEC Técnica - Sprint 013 Backfill & Queue Normalization V0

## Comando

`factory-state-backfill-sprint-013`

## Fontes de evidência

- `git log --oneline --all`
- `specs/sprints/013*`
- `specs/technical-spec/*readiness*`
- `specs/prd/*readiness*`
- `specs/discovery/*readiness*`
- `reports/*readiness*`
- `reports/*worktree*`

## Fluxo

1. confirmar repo limpo;
2. localizar a task `20260430-134542-sprint-013-worktree-sync-readiness-gate-ae42c9`;
3. confirmar status `running`;
4. confirmar o commit `7c53cd5`;
5. confirmar a presença de `run-workspace-readiness`;
6. coletar evidências locais por glob e por texto;
7. consultar `factory-state-plan`;
8. se todos os critérios mínimos passarem:
   registrar nota de backfill e executar `task-finish`;
9. caso contrário:
   manter `closed=false` e `decision=needs_review` ou `blocked`.

## Modelo de report

O report precisa incluir:

- `kind = sprint-013-backfill`
- `task_id`
- `task_status_before`
- `task_status_after`
- `git_commit.found`
- `command_checks.run_workspace_readiness_present`
- `factory_state_plan_decision`
- `criteria`
- `evidence_files`
- `decision`
- `closed`
- `before_stats`
- `after_stats`
- `executed_mutations`
- `deleted_files = []`
- `removed_worktrees = []`
- `executed_live = false`

## Guardrails

- se houver dúvida, `needs_review`;
- sem apagar dados;
- sem remover worktree;
- sem live Codex;
- sem merge/rebase/fetch/pull.
