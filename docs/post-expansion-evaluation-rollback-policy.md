# Post-Expansion Evaluation & Rollback Policy V0

Objetivo: avaliar formalmente o canário expandido da Sprint 057 e gerar uma política de rollback segura, sem aplicar rollback automaticamente.

## Avaliação

1. ler o report do canário expandido;
2. validar duração, steps, heads, arquivos e flags de segurança;
3. confirmar que o `token_summary` está em limite razoável;
4. classificar o resultado como `passed`, `needs_review` ou `failed`.

## Rollback

1. aceitar apenas `--dry-run`;
2. listar os arquivos que seriam revertidos se houver necessidade;
3. marcar `safe_to_apply=false` por padrão;
4. marcar `human_review_required=true`.

## Segurança

- não aplicar rollback automaticamente;
- não tocar em secrets, billing, deploy ou infra pública;
- a decisão final continua auditável por report.
