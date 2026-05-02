# PRD - Compact Execution Harness V0

## Problema

Mesmo com output budget, o FactoryOS ainda precisa de uma política clara por categoria para impedir logs e summaries excessivos.

## Objetivo

Criar um harness compacto com budgets por categoria, check local de logs e report consolidado.

## Não objetivos

- não executar live neste sprint;
- não mudar a política de 30m/6 steps;
- não remover comandos antigos;
- não apagar reports;
- não usar API paga.

## Comandos esperados

- `compact-exec-budget`
- `compact-exec-check --log <PATH> --category <CATEGORY>`
- `compact-exec-report --log <PATH> --category <CATEGORY>`

## Integração

- `run-handoff` deve recomendar `codex-quiet-run`;
- `factory-start` deve registrar recomendação de quiet runner;
- `raw_codex_exec_allowed` deve ficar falso por padrão.

## Critérios de pronto

- budgets por categoria disponíveis;
- check bloqueia logs acima do budget;
- report grava prova compacta;
- handoff carrega recomendação de quiet runner;
- sem live executado.
