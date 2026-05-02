# Technical Spec - Factory Start Capsule Mode V0

## Objetivo

Acoplar a policy de cápsula ao `factory-start` e ao `run-handoff`.

## Integração

- `run-handoff` passa a expor campos de policy;
- `factory-start --plan-only --cost-aware` passa a mostrar a recomendação de executor;
- `factory-start` não executa live nesta sprint;
- decisões de segurança continuam em full_repo_review.

## Requisitos de reporte

- `execution_mode_recommendation`
- `capsule_recommended`
- `capsule_policy_decision`
- `expected_savings_percent`
- `full_repo_required_reason`
- `timeout_recovery_policy`

## Validação

- create task/run barata de canário;
- gerar run-handoff;
- gerar plan-only cost-aware;
- confirmar que `capsule_recommended=true` para docs_only/code_small;
- confirmar que `executed_live=false`;
- confirmar `allowed_to_execute_live=false`.
