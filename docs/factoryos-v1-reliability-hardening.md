# FactoryOS V1 Reliability Hardening V0

Check local de confiabilidade operacional da V1.

## Comando

- `factoryos-v1-reliability-check --dry-run`
- equivalente local: `python -m app.cli factoryos-v1-reliability-check --dry-run`

## Escopo

- comandos principais retornam JSON válido;
- `codex-run-result-check` aceita warning budget como sucesso com warning;
- readiness gate continua executável;
- `report-latest` e `report-list` continuam úteis;
- painel abre com `GET / = 200`;
- comandos demo de runbook e evaluator funcionam;
- erro esperado retorna mensagem controlada.

## Saída

O report é salvo em `reports/reliability-hardening/<timestamp>.json` com:

- `reliability_decision`: `passed`, `needs_review` ou `failed`;
- `blockers`;
- `warnings`;
- `fixed_items`;
- `executed_live=false`.

## Regras

- não executa live;
- não faz push;
- não faz deploy;
- não usa API paga;
- mantém outputs compactos.
