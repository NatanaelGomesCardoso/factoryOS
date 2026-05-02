# PRD - Sprint 013 Backfill & Queue Normalization V0

## Problema

A Sprint 013 permaneceu em `running` mesmo com evidências locais de entrega, deixando a fila ambígua para higiene e seleção automática do loop.

## Objetivo

Auditar a Sprint 013, localizar prova local suficiente, gerar um backfill report e fechar a task somente quando os critérios mínimos forem atendidos.

## Reuso primeiro

- `factory-state-audit`
- `factory-state-plan`
- `task-show`, `task-note`, `task-finish`
- `git log`
- specs/proofs/reports existentes

## Critérios mínimos de evidência

- a task da Sprint 013 existe e está em `running`;
- o commit `7c53cd5 feat: add worktree readiness gate v0` existe no histórico;
- o comando `run-workspace-readiness` existe no código/CLI;
- existem specs/reports relacionados a readiness/worktree;
- não há run `running` ligada à Sprint 013;
- o plano de higiene não classifica a Sprint 013 como `blocked`;
- o repo está limpo antes da mutação.

## Política de decisão

- fechar apenas quando todos os critérios mínimos forem verdadeiros;
- se houver dúvida, registrar `needs_review`;
- nunca apagar arquivos;
- nunca remover worktree;
- nunca executar Codex live;
- nunca fazer merge, rebase, fetch ou pull.

## Critérios de pronto

- report JSON em `reports/factory-state-hygiene/`;
- proof textual da Sprint 020;
- Sprint 013 fechada somente se houver prova suficiente;
- fila final sem ambiguidade adicional.
