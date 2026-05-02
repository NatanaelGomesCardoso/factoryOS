# FactoryOS V1 Security Hardening V0

Revisão defensiva dos contratos de segurança e safety da V1.

## Comando

- `factoryos-v1-security-review --dry-run`
- equivalente local: `python -m app.cli factoryos-v1-security-review --dry-run`

## Escopo

- comandos perigosos exigem flags explícitas ou dry-run;
- painel e viewer são read-only e bloqueiam traversal;
- artifact intake bloqueia extensões perigosas;
- delivery package exclui secrets, `.env`, caches e artefatos locais;
- Obsidian sync fica dentro do vault permitido;
- retention cleanup gera plano sem apagar ou mover arquivos;
- apply plan mantém `human_review_required=true` e `safe_to_apply=false`;
- frontend/backend split documenta que secrets e regra crítica ficam fora do frontend;
- docs/reports textuais são escaneados para tokens óbvios.

## Saída

O report é salvo em `reports/security-safety-reviews/<timestamp>.json` com:

- `security_decision`: `passed`, `needs_review` ou `failed`;
- `blockers`;
- `warnings`;
- `fixed_items`;
- `executed_live=false`.

## Regras

- não faz push;
- não faz deploy;
- não usa API paga;
- não publica nada;
- não aplica mudanças reais sem gate humano.
