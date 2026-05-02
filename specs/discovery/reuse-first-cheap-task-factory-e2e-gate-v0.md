# Reuse First - Cheap Task Factory E2E Gate V0

## Ideia

Conectar policy, cápsula, quiet runner, diff e export-plan em um gate barato de ponta a ponta.

## Reuso

- `app/capsule_execution_policy.py`
- `app/codex_context_capsule.py`
- `app/codex_capsule_execution.py`
- `app/compact_execution_harness.py`

## Resultado esperado

- política aponta para `capsule` em `docs_only` e `code_small`;
- o canário cria somente `cheap-task-e2e-canary.txt` dentro da cápsula;
- o report final consolida economia, segurança e decisão final.

