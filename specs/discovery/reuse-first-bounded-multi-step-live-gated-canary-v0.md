# Reuse First — Bounded Multi-Step Live-Gated Canary V0

## Objetivo

Liberar um canário live multi-step pequeno e rigorosamente gated no `factory-start`, sem virar execução longa.

## Reuso obrigatório

- reaproveitar `factory-start` live canary;
- reaproveitar `execution-evaluate`;
- reaproveitar `run workspace` isolado;
- reaproveitar `report_index`;
- reaproveitar readiness e sync-plan gates.

## Decisão V0

- live multi-step somente em modo `--live --canary --evaluate`;
- `run_id` explícito obrigatório;
- `FACTORYOS_ENABLE_LIVE_CODEX=1` obrigatório;
- `max_steps` permitido apenas entre `1` e `2`;
- alterações restritas a arquivos canary permitidos;
- sem retry e sem execução longa.

## Fora de escopo

- loop de 6h;
- scheduler;
- daemon;
- produção;
- merge;
- push;
- deploy.
