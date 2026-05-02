# FactoryOS V1 Readiness Gate V0

Gate local de prontidão para decidir se o FactoryOS já pode avançar para auditoria e lapidação.

## Comando

- `factoryos-v1-readiness-gate --dry-run`

## Checks

- comandos principais existem;
- reports principais existem;
- `GET /` do painel retorna 200;
- `git diff --check` passa;
- templates estão disponíveis;
- workspace demo existe;
- evaluator funciona;
- delivery package dry-run funciona;
- retention cleanup dry-run funciona;
- Obsidian sync dry-run funciona;
- quiet runner status contract funciona.

## Decisão

- `ready_for_audit`;
- `needs_review`;
- `failed`.

## Nunca automático

- push;
- deploy;
- API paga;
- secrets.
