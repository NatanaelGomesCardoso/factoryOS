# Technical Spec — Report Retention & Worktree Lifecycle V0

## Módulos

- `app/report_retention.py`
- `app/worktree_lifecycle.py`
- `app/maintenance_plan.py`

## Regras

- Tudo é read-only, exceto gravação do próprio report do plano.
- `report-retention-plan` faz inventário recursivo em `reports/`.
- `worktree-lifecycle-plan` lê `git worktree list --porcelain` e cruza com `runs/`.
- `factory-maintenance-plan` executa os dois planos acima e agrega `factory-state-audit/plan`.

## Segurança

- Nunca chamar `git worktree remove`, `git clean`, `git gc`.
- Nunca apagar ou mover reports no V0.
- Expor `deleted_files=none` e `removed_worktrees=none` no payload.
