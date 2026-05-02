# Technical Spec - Long Run Controlled Dry-Run Rehearsal V0

## Fluxo

1. validar `run_id`, `target_minutes`, `max_steps` e `--dry-run`;
2. exigir run em `running`;
3. checar `run-workspace-readiness` e `run-workspace-sync-plan`;
4. gerar planner longo e maintenance plan;
5. reaproveitar o último `codex-cost-audit` aceitável ou rodar um novo;
6. rodar `factory-start --plan-only --cost-aware`;
7. rodar `factory-start --dry-run --cost-aware --evaluate --max-steps 2`;
8. gravar report em `reports/factory-long-run-rehearsals/`.

## Decisão final

- `dry_run_only` quando readiness, sync atual, custo, budget e contexto estiverem ok e o dry-run cost-aware também terminar em `dry_run_only`;
- `needs_review` para qualquer outro caso.
