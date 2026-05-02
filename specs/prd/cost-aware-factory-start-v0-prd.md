# PRD — Cost-Aware Factory Start V0

## Problema

O `factory-start` já roda dry-run, mas ainda não consolida explicitamente custo, contexto, manutenção e planejamento longo antes da decisão operacional.

## Objetivo

Integrar routing contracts, long-run planner, maintenance plan e codex cost audit ao `factory-start`, com `--plan-only` e `--cost-aware`, mantendo live bloqueado.

## Requisitos

- `factory-start --plan-only --cost-aware --run-id <RUN_ID> --target-minutes 30 --max-steps 6`
- `factory-start --dry-run --cost-aware --run-id <RUN_ID> --max-steps 2 --evaluate`
- `factory-start --live --cost-aware` deve bloquear com mensagem clara
- report em `reports/cost-aware-factory-starts/`
- `global_config_dependency=false`
- `executed_live=false`

## Não Objetivos

- liberar live;
- executar Codex live;
- mudar harness ou config global;
- limpar reports/worktrees.
