# PRD — Factory Start Evaluated Run V0

## Problema

O `factory-start` já executa dry-run bounded e live canary mínimo, mas ainda falta consolidar a decisão final no próprio fluxo. Hoje a avaliação existe como passo separado e isso mantém ambiguidade operacional.

## Objetivo

Integrar execução e avaliação numa única operação bounded:

- dry-run avaliado;
- live canary avaliado;
- decisão final explícita;
- sem loop longo e sem automação agressiva.

## Requisitos

1. `factory-start --dry-run --evaluate` deve gerar report do start e report da avaliação.
2. `factory-start --live --canary --evaluate` deve gerar report live e report da avaliação.
3. Dry-run avaliado não pode virar `passed` por falta de evidência live.
4. Live canary só pode virar `passed` se a avaliação também retornar `passed`.
5. O painel deve continuar read-only e mostrar a decisão final mais recente.

## Não objetivos

- scheduler;
- daemon;
- multi-step longo;
- merge/push/deploy;
- integração externa.
