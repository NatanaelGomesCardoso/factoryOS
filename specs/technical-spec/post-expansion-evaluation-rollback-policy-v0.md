# Technical Spec - Post Expansion Evaluation & Rollback Policy V0

## Fluxo

1. carregar o report da Sprint 057;
2. validar steps, duração, heads, arquivos e flags;
3. classificar `final_decision` em `passed`, `needs_review` ou `failed`;
4. produzir evaluation report com `token_summary` e checks;
5. produzir rollback plan em dry-run com lista de arquivos reversíveis;
6. manter `safe_to_apply=false` e `human_review_required=true`.

## Segurança

- não aplicar rollback automaticamente;
- não tocar em infra pública, billing ou secrets;
- não aceitar report fora de `reports/expanded-bounded-live-canary/`;
- um resultado com `needs_review` não é falha automática.

## Validação

- `py_compile`;
- `compileall`;
- `git diff --check`;
- `TestClient GET / = 200`.
