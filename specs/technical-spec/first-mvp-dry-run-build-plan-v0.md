# SPEC Técnica - First MVP Dry-Run Build Plan V0

## Decisão

Adicionar um comando que leia um report de intake e produza um plano de build dry-run com tasks planejadas e split backend/frontend.

## Regras

1. aceitar somente `--dry-run`;
2. ler um report de intake existente;
3. derivar tasks a partir dos candidates;
4. marcar `docs_only` e `code_small` para capsule;
5. bloquear push, deploy, API paga e secrets;
6. gravar report em `reports/mvp-build-plans/`.

## Campos principais

- `executed_live=false`;
- `planned_tasks`;
- `planned_components`;
- `routing_summary`;
- `report_path`.

