# MVP Validation & Evaluator V0

Evaluator local para revisar workspaces MVP e produzir uma decisão estruturada.

## Checks

- `README.md`
- `PROJECT_STATE.md`
- `backend/` quando exigido
- `frontend/` quando exigido
- `docs/`
- `reports/`
- arquivos proibidos óbvios
- segredos óbvios por padrões simples
- separação backend/frontend documentada
- `no_push=true`, `no_deploy=true`, `no_paid_api=true`, `no_secrets=true`

## Saída

- `final_decision = passed | needs_review | failed`
- report em `reports/mvp-evaluations/`

