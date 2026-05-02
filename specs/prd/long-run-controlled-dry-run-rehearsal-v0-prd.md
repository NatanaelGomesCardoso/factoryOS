# PRD - Long Run Controlled Dry-Run Rehearsal V0

## Contexto

O FactoryOS já possui planner dry-run, maintenance plan, cost audit e `factory-start` cost-aware, mas ainda falta um rehearsal consolidado para provar o gate de rodada longa sem executar live.

## Objetivo

Entregar um rehearsal único, explícito e repetível que confirme readiness, sync-plan, budget, contexto e custo antes do próximo gate manual.

## Requisitos

1. O comando exige `--run-id` explícito e `--dry-run`.
2. A run precisa estar em `running`.
3. O rehearsal roda `factory-long-run-plan`, `factory-maintenance-plan`, `factory-start --plan-only --cost-aware` e `factory-start --dry-run --cost-aware --evaluate`.
4. O report final sempre registra `allowed_to_execute_live=false` e `executed_live=false`.
5. O resultado final é apenas `dry_run_only` ou `needs_review`.
