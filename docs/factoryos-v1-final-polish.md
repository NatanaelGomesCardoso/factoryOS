# FactoryOS V1 Final Polish & Consistency Pass V0

Lapidação técnica final antes do fechamento formal da V1.

## Comando

- `factoryos-v1-polish-check --dry-run`
- equivalente local: `python -m app.cli factoryos-v1-polish-check --dry-run`

## Escopo

- confirma nomes de comandos principais na CLI e na documentação;
- confirma reports críticos de readiness, audit, security e reliability;
- valida JSON dos comandos principais da V1;
- confirma flags `no_push`, `no_deploy`, `no_paid_api` e `no_secrets` nos reports críticos;
- executa novamente readiness, audit, security e reliability em dry-run;
- verifica documentação operacional principal;
- confirma painel com `GET / = 200`.

## Saída

O comando salva um report JSON em `reports/final-v1-polish-consistency-pass/<timestamp>.json` e atualiza `reports/final-v1-polish-consistency-pass-v0-proof.txt`.

Campos principais:

- `polish_decision`: `passed`, `needs_review` ou `failed`;
- `blockers`;
- `warnings`;
- `fixed_items`;
- `executed_live=false`.

## Regras

- não executa live;
- não faz push;
- não faz deploy;
- não usa API paga;
- não altera segredos;
- não adiciona feature grande.
