# PRD - Factory Multi-Task Start Queue V0

## Problema

O FactoryOS precisa iniciar uma fila curta de tasks sem virar automacao solta ou executar live sem gate.

## Objetivo

Planejar ate 3 tasks por vez, de forma controlada, respeitando routing e custo.

## Requisitos

- `factory-queue-start --dry-run --max-tasks 3 --cost-aware`
- `factory-queue-start --plan-only --max-tasks 3 --cost-aware`
- `max_tasks` padrao 3
- `max_tasks` maximo 5
- `max_steps_per_task` padrao 1
- sem execucao live
- report em `reports/factory-queue-starts/`

## Regras de routing

- `docs_only` -> `capsule`
- `code_small` -> `capsule`
- `security_review` e `heavy_review_only` -> `full_repo_review` ou `blocked`
- `live_canary` -> `gated_only`

## Nao objetivos

- mover tasks para done automaticamente;
- executar Codex live;
- iniciar deploy;
- mexer em secrets.
