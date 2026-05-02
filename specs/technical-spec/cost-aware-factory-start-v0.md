# Technical Spec — Cost-Aware Factory Start V0

## Integração

`app/factory_start.py` passa a ter uma trilha cost-aware que:

- lê routing contract da run/task;
- lê `codex-plan` e `codex-context`;
- lê `factory-long-run-plan`;
- lê `factory-maintenance-plan`;
- lê o último `codex-cost-audit`.

## Modos

- `plan-only`: não executa loop nem Codex, apenas escreve o report consolidado.
- `dry-run`: só executa o dry-run existente se budget/contexto/manutenção/custo estiverem aceitáveis.
- `live`: bloqueado explicitamente.

## Segurança

- `allowed_to_execute_live=false` sempre;
- `executed_live=false` sempre nesta sprint;
- `global_config_dependency=false` sempre;
- qualquer bloqueio de budget/contexto/maintenance derruba a decisão para `blocked`.
