# SPEC Técnica - MVP Apply Plan & Human Review Gate V0

## Decisão

Adicionar um comando que converta o canary em um plano de aplicação com revisão humana obrigatória.

## Regras

1. aceitar somente `--dry-run`;
2. ler o report do canary;
3. extrair `would_apply_files`;
4. expor `disallowed_files`;
5. marcar `human_review_required=true`;
6. manter `safe_to_apply=false`;
7. não alterar o repo real.

## Campos principais

- `human_review_required`;
- `safe_to_apply`;
- `safe_to_apply_later`;
- `would_apply_files`;
- `disallowed_files`;
- `report_path`.

