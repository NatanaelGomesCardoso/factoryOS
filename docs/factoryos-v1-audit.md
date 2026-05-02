# FactoryOS V1 Audit V0

Auditoria local de consistência para a V1 antes da rodada final.

## Comando

- `factoryos-v1-audit --dry-run`
- equivalente local: `python -m app.cli factoryos-v1-audit --dry-run`

## Escopo

- verifica comandos principais da CLI;
- verifica reports principais indexados;
- valida templates MVP;
- confirma workspace demo e evaluator;
- executa o readiness gate em dry-run;
- verifica painel `GET /`;
- valida `codex-run-result-check` com orçamento ok e warning;
- confere docs/specs relevantes;
- checa nomes de comandos em docs;
- confirma flags de safety e `git diff --check`.

## Saída

O report é salvo em `reports/factoryos-v1-audits/<timestamp>.json` com:

- `audit_decision`: `passed`, `needs_review` ou `failed`;
- `blockers`;
- `warnings`;
- `suggested_fixes`;
- `executed_live=false`.

## Regras

- não faz push;
- não faz deploy;
- não usa API paga;
- não toca em secrets;
- não executa fluxo live.
