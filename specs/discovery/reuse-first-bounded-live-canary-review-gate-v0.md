# Reuse First - Bounded Live Canary Review Gate V0

## Objetivo

Reusar os reports já produzidos pela Sprint 035 para formalizar um review gate local, sem executar live novo, e sem liberar expansão automaticamente.

## Reuso confirmado

- `app/factory_start.py`
- `app/report_index.py`
- `app/execution_evaluator.py`
- `app/codex_cost_audit.py`
- `reports/bounded-long-run-live-canary/`
- `reports/execution-evaluations/`
- `reports/codex-cost-audits/`
- `reports/factory-maintenance-plans/`

## Saída esperada

- comando `bounded-live-canary-review --run-id <RUN_ID>`
- report em `reports/bounded-live-canary-reviews/`
- proof local em `reports/bounded-live-canary-review-gate-v0-proof.txt`
