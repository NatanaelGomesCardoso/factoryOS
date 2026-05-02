# PRD - Factory Start Capsule Mode V0

## Resumo

Integrar a policy de cápsula ao caminho `factory-start` e ao `run-handoff`.

## Problema

O fluxo de start ainda precisava expor, de forma explícita, quando usar cápsula em vez de repo completo.

## Objetivo

- mostrar a decisão de execução econômica no plano;
- propagar a decisão para o handoff;
- preservar `--plan-only` como caminho sem live;
- manter canário live fora desta sprint.

## Requisitos

- `run-handoff` com campos de policy;
- `factory-start --plan-only --cost-aware` informativo;
- savings esperado com baseline conhecido;
- canário dry-run de validação;
- validações locais sem execução live.

## Fora de escopo

- live execution nesta sprint;
- deploy;
- push/pull/fetch/rebase;
- segredos.
