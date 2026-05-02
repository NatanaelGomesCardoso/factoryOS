# PRD - Token Economy & Output Budget Enforcement V0

## Problema

O FactoryOS está acumulando custo desnecessário porque saídas grandes de CLI, handoffs verbosos e summaries finais longos entram como output e depois voltam como input.

## Objetivo

Criar um contrato local e reutilizável para limitar stdout, resumir tokens e registrar evidência em reports curtos.

## Não objetivos

- não mudar a regra crítica do backend;
- não automatizar live;
- não usar API paga;
- não instalar dependência externa nova;
- não reescrever comentários ou código do usuário.

## Comandos esperados

- `python -m app.cli output-budget-contract`
- `python -m app.cli token-usage-parse --log <PATH>`
- `python -m app.cli output-budget-check --log <PATH> --max-lines <N> --max-bytes <N>`
- `python -m app.cli codex-output-budget-report --log <PATH>`

## Segurança

- não imprimir segredo;
- não despejar task-list/run-list completo em prompt;
- não aceitar terminal gigante como padrão;
- guardar evidência em `reports/`.

## Critérios de pronto

- contrato compacto disponível por CLI;
- parser de token usage funciona em logs simples e detalhados;
- output budget check classifica `ok`, `warn` e `blocked`;
- run-handoff carrega o contrato explícito;
- factory-start prompts carregam o contrato explícito;
- repo segue validando com `git diff --check`.
