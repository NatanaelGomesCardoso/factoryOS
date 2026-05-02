# Factory Multi-Task Start Queue V0

Este documento descreve a fila curta controlada do FactoryOS para iniciar multiples tasks sem virar automacao solta.

## Objetivo

- Planejar ate 3 tasks por vez por padrao.
- Manter o fluxo em dry-run ou plan-only.
- Respeitar routing local e custo.
- Nunca tocar em tasks running ou failed.

## Regras

- `docs_only` -> `capsule`
- `code_small` -> `capsule`
- `security_review` e `heavy_review_only` -> `full_repo_review` ou `blocked`
- `live_canary` -> `gated_only`

## Saida

O comando `factory-queue-start` grava report local em `reports/factory-queue-starts/` e nao executa live.
