# MVP Apply Plan & Human Review Gate V0

Comando local para criar um plano de aplicação depois do canary, mas sem aplicar nada automaticamente.

## Fluxo

- lê o report do canary;
- extrai os arquivos que seriam aplicados;
- bloqueia `disallowed_files`;
- marca revisão humana obrigatória;
- grava report em `reports/mvp-apply-plans/`.

## Resultado esperado

- `human_review_required=true`;
- `safe_to_apply=false`;
- nenhum arquivo real alterado;
- base para revisão humana antes da aplicação.

