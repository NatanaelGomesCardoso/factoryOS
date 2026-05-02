# PRD - Post Expansion Evaluation & Rollback Policy V0

## Objetivo

Avaliar formalmente o canário expandido da Sprint 057 e gerar um plano de rollback/recovery em dry-run, sem aplicar rollback automaticamente.

## Requisitos

1. comando `post-expansion-evaluate --report <REPORT_PATH>`;
2. comando `post-expansion-rollback-plan --report <REPORT_PATH> --dry-run`;
3. report de evaluation em `reports/post-expansion-evaluations/`;
4. report de rollback plan em `reports/post-expansion-rollback-plans/`;
5. `safe_to_apply=false` por padrão e `human_review_required=true`;
6. avaliar `passed`, `needs_review` ou `failed`.

## Segurança

- rollback não pode ser automático;
- somente leitura do report de entrada;
- sem push, deploy, API paga ou secrets;
- qualquer decisão de reversão precisa ficar explícita no report.
