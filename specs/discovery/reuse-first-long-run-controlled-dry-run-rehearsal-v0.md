# Reuse First - Long Run Controlled Dry-Run Rehearsal V0

## Objetivo

Consolidar planner, maintenance, cost audit e factory-start cost-aware em um rehearsal único, somente dry-run, com report explícito e gate manual antes de qualquer bounded live futuro.

## Reuso confirmado

- `app/long_run_planner.py`
- `app/maintenance_plan.py`
- `app/codex_cost_audit.py`
- `app/factory_start.py`
- `app/execution_evaluator.py`
- `app/report_index.py`

## Saída esperada

- comando `factory-long-run-rehearsal --run-id <RUN_ID> --target-minutes 30 --max-steps 6 --dry-run`
- report em `reports/factory-long-run-rehearsals/`
- proof local em `reports/long-run-controlled-dry-run-rehearsal-v0-proof.txt`
