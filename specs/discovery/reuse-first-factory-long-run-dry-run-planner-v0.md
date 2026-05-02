# Reuse First — Factory Long Run Dry-Run Planner V0

## Objetivo

Planejar rodadas longas sem executar nada live, usando apenas sinais já disponíveis no FactoryOS.

## Reaproveitar

- `run_workspace_readiness` e `run_workspace_sync_plan`;
- `codex-plan` e `codex-context`;
- `factory-state-audit` e `factory-state-plan`;
- seleção de runs do `controlled_loop`.

## Decisão V0

Criar `app/long_run_planner.py` como orquestrador read-only que gera um report consolidado com estimativas, gates, riscos e blockers, sempre com `allowed_to_execute_live=false`.

## Fora de Escopo

- executar live;
- loop de 6h;
- scheduler, daemon ou paralelismo;
- mutação automática de worktree/reports.
