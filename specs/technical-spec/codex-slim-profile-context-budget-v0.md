# Technical Spec — Codex Slim Profile Context Budget V0

## Arquitetura

Adicionar `app/codex_profile.py` como módulo local de política. O módulo lê task/run via APIs existentes, estima contexto com arquivos mínimos (`AGENTS.md`, `WORKFLOW.md`, task e run JSON) e retorna plano JSON.

## Integrações

- `app/cli.py`: comandos `codex-profile-list` e `codex-plan`.
- `app/codex_handoff.py`: incluir `codex_plan`, `codex_profile`, `model`, `reasoning_effort`, `context_budget` e `budget_status`.
- Reports continuam em `reports/`.

## Gate

`validate_codex_budget(plan)` define `budget_status=blocked` quando:

- `estimated_context_chars > max_context_chars`;
- `estimated_changed_files > max_changed_files`;
- plano live usa perfil fora de `codex_standard_medium` ou `codex_heavy_review_only`.

## Segurança

Validação de ids continua nas APIs existentes. O plano não executa Codex, não toca config global e não lê secrets.
