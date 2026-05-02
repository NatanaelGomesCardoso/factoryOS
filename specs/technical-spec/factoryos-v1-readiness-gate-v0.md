# SPEC Técnica - FactoryOS V1 Readiness Gate V0

## Decisão

Implementar um gate de leitura local que consolida checagens do repositório e retorna `ready_for_audit`, `needs_review` ou `failed`.

## Checks mínimos

- comandos principais existem no parser;
- reports principais existem;
- `GET /` retorna 200 no painel;
- `git diff --check` passa;
- flags de segurança permanecem em `true`;
- templates estão disponíveis;
- workspace demo existe;
- evaluator funciona;
- delivery package dry-run funciona;
- retention cleanup dry-run funciona;
- Obsidian sync dry-run funciona;
- quiet runner status contract funciona.

## Contrato de saída

- `ok=true`;
- `dry_run=true`;
- `readiness_decision` explícito;
- `human_review_required` coerente com a decisão;
- report salvo em `reports/factoryos-v1-readiness-gates/`.

## Regras

- não fazer push;
- não fazer deploy;
- não usar API paga;
- não expor secrets;
- não corrigir o estado automaticamente.
