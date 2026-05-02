# PRD - Expanded Long Run Review Gate V0

## Problema

O rehearsal expandido precisa de um gate formal que leia as evidências, revise o estado atual e diga se uma sprint futura pode, em tese, executar live 30m/6 steps.

## Objetivo

Gerar um review gate explícito para o rehearsal expandido da Sprint 038, sem liberar live diretamente.

## Regras

- Não executar live.
- Manter `allowed_to_execute_live=false`.
- Manter `next_gate_requires_new_sprint=true`.
- Aprovar apenas se rehearsal, maintenance, state e evidências estiverem consistentes.

## Saída

Report JSON com decisão `approved_for_expanded_live_sprint`, `needs_review` ou `blocked`.

## Critérios de sucesso

- Report legível pelo painel.
- Revisão conservadora de evidências.
- Recomendação explícita da próxima sprint.
