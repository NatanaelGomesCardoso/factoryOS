# PRD — Bounded Multi-Step Factory Start Dry-Run V0

## Problema

O `factory-start` já prova um passo bounded, mas ainda não demonstra sequência controlada com mais de um step nem consolida um report multi-step.

## Objetivo

Entregar um `factory-start --dry-run` bounded com `2` ou `3` steps, sem live, com avaliação conservadora e report unificado.

## Requisitos

1. `factory-start --dry-run --run-id <RUN_ID> --max-steps 2 --evaluate` deve executar steps sequenciais.
2. Cada step deve reaproveitar `factory-loop` V1 em `dry-run`.
3. O report deve expor `steps_requested`, `steps_completed` e `steps[]`.
4. A decisão final deve ser conservadora:
   - `dry_run_only` se todos os steps forem secos e válidos;
   - `blocked` se pré-condições falharem;
   - `failed` se validações locais falharem;
   - `needs_review` se houver ambiguidade.
5. O fluxo deve manter `executed_live=false`.

## Não objetivos

- execução live;
- loop longo;
- retry automático;
- daemon ou scheduler;
- merge, push ou deploy.
