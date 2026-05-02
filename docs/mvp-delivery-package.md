# MVP Delivery Package V0

Comando para listar o pacote local de entrega de um MVP sem criar zip nem fazer deploy.

## Comando

- `mvp-delivery-package-create --project <NAME> --workspace <PATH> --dry-run`

## Regras

- somente `--dry-run` nesta V0;
- incluir `README.md`, `PROJECT_STATE.md`, docs e reports do workspace;
- excluir secrets, caches, `node_modules`, `.venv` e `__pycache__`;
- marcar `package_created=false` e `human_review_required=true`;
- manter `no_push=true`, `no_deploy=true`, `no_paid_api=true`, `no_secrets=true`.
