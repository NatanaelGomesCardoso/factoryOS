# First MVP Dry-Run Build Plan V0

Comando local para transformar um report de project intake em plano de build sem executar build real.

## Fluxo

- lê um report de `project-intake`;
- gera tasks planejadas com separação `backend` e `frontend`;
- mantém `docs_only` e `code_small` como candidatos para capsule;
- bloqueia push, deploy, API paga e secrets;
- grava report local em `reports/mvp-build-plans/`.

## Resultado esperado

- `executed_live=false`;
- `dry_run=true`;
- tasks planejadas auditáveis;
- base para o canary de cápsula da sprint seguinte.

