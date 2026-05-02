# Report Retention & Cleanup Policy V1

Política read-only para classificar reports por idade, tamanho e categoria.

## Comandos

- `report-retention-audit --dry-run`
- `report-retention-cleanup-plan --dry-run`

## Regras

- não apagar nada;
- sugerir `keep`, `archive` ou `delete_candidate`;
- `delete_candidate` sempre requer revisão humana;
- `safe_to_apply=false` sempre;
- `no_push=true`, `no_deploy=true`, `no_paid_api=true`, `no_secrets=true`.
