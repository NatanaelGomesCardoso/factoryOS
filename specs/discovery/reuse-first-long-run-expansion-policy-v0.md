# Reuse First - Long Run Expansion Policy V0

## Objetivo

Reusar o review gate aprovado da Sprint 036 para formalizar a política de expansão futura do long run live, sem executar live novo.

## Reuso confirmado

- `app/live_canary_review_gate.py`
- `app/long_run_expansion_policy.py`
- `app/report_index.py`
- `app/codex_cost_audit.py`
- `app/maintenance_plan.py`
- `app/state_hygiene.py`
- `reports/bounded-live-canary-reviews/`
- `reports/codex-cost-audits/`
- `reports/factory-maintenance-plans/`
- `reports/factory-state-hygiene/`

## Saída esperada

- comando `long-run-expansion-policy --run-id <RUN_ID> --target-minutes 30 --max-steps 6`
- report em `reports/long-run-expansion-policies/`
- proof local em `reports/long-run-expansion-policy-v0-proof.txt`
