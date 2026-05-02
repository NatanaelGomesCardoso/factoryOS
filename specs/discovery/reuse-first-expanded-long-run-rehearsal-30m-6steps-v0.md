# Reuse First Discovery - Expanded Long Run Rehearsal 30m/6 Steps V0

## Objetivo

Consolidar um rehearsal expandido em dry-run para 30 minutos e 6 steps, reutilizando a policy de expansão da Sprint 037, o rehearsal controlado da Sprint 034, o maintenance plan e o factory state hygiene já existentes.

## Reuso prioritário

- `app/long_run_rehearsal.py`
- `app/long_run_expansion_policy.py`
- `app/maintenance_plan.py`
- `app/state_hygiene.py`
- `app/report_index.py`

## Decisão de reuso

- Reusar a policy aprovada da Sprint 037 como gatilho de entrada.
- Reusar o rehearsal controlado da Sprint 034 como base operacional.
- Reusar maintenance/state/cost audit existentes em vez de introduzir caminhos novos.
- Não criar live, daemon, scheduler, App Server novo, MCP novo ou integração externa.

## Resultado esperado

Um rehearsal expandido com report explícito, sem live, com evidência suficiente para alimentar um review gate formal na próxima sprint.
