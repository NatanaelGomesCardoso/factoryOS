# Reuse First Discovery - Expanded Long Run Review Gate V0

## Objetivo

Revisar formalmente o rehearsal expandido 30m/6 steps, reutilizando o report da Sprint 038 e o state/maintenance cost-aware já existentes para decidir se uma sprint futura pode seguir para live bounded.

## Reuso prioritário

- `app/expanded_long_run_rehearsal.py`
- `app/long_run_expansion_policy.py`
- `app/maintenance_plan.py`
- `app/state_hygiene.py`
- `app/report_index.py`

## Decisão de reuso

- Reusar a evidência consolidada da Sprint 038.
- Reusar manutenção/state atuais em vez de recalcular política nova.
- Manter `allowed_to_execute_live=false`.
- Manter `next_gate_requires_new_sprint=true`.

## Resultado esperado

Um review gate explícito e conservador, com decisão aprovada ou bloqueada sem liberar live diretamente.
