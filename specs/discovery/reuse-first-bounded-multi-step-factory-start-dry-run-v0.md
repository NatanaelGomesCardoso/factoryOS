# Reuse First — Bounded Multi-Step Factory Start Dry-Run V0

## Objetivo

Evoluir o `factory-start` para provar mais de um step em `dry-run`, de forma síncrona, bounded e sem liberar execução live.

## Reuso obrigatório

- reaproveitar `factory-start` V0;
- reaproveitar `factory-loop` V1 por step;
- reaproveitar `execution-evaluate`;
- reaproveitar `report_index`;
- reaproveitar os gates de `run-workspace-readiness` e `run-workspace-sync-plan`.

## Decisão V0

- multi-step apenas em `dry-run`;
- execução síncrona e controlada;
- `max_steps` permitido entre `1` e `3`;
- um `factory-loop` V1 por step;
- report consolidado com `steps[]`;
- `executed_live=false` em todo o fluxo.

## Fora de escopo

- daemon;
- scheduler;
- live multi-step;
- retry loop;
- merge;
- push;
- deploy.
