# PRD - Expanded Long Run Rehearsal 30m/6 Steps V0

## Problema

O FactoryOS já prova rehearsal dry-run e canary live limitado, mas ainda não tem uma evidência consolidada para o nível expandido de 30 minutos e 6 steps sem liberar live.

## Objetivo

Gerar um rehearsal expandido, só em dry-run, que consolide custo, contexto, readiness, sync, maintenance e policy de expansão.

## Regras

- Não executar live.
- Manter `allowed_to_execute_live=false`.
- Manter `executed_live=false`.
- Exigir policy de expansão aprovada da Sprint 037.
- Exigir `target_minutes=30` e `max_steps=6`.
- Exigir report explícito em `reports/expanded-long-run-rehearsals/`.

## Saída

Report JSON com decisão `expanded_rehearsal_ready_for_review` quando não houver bloqueios, ou `needs_review`/`blocked` quando evidências não forem suficientes.

## Critérios de sucesso

- Report válido e legível pelo painel.
- Validation local reproduzível.
- Sem dependência de config global para autorização.
- Sem mutação live.
