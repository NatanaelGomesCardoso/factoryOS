# Factory Start Capsule Mode V0

## O que é

Integração do `factory-start` com a policy de cápsula para que tarefas baratas usem o caminho econômico por padrão.

## Para que serve

- deixar explícito quando usar `capsule`, `repo_quiet` ou `full_repo_review`;
- propagar a decisão para `run-handoff`;
- mostrar economia esperada antes de qualquer execução live;
- manter `factory-start --plan-only --cost-aware` como dry-run informativo;
- evitar ativar live nesta sprint.

## Requisitos

- `run-handoff` expõe recomendação de modo, decisão de policy, savings esperado e política de timeout;
- `factory-start --plan-only --cost-aware` informa se usaria cápsula, repo_quiet ou full_repo_review;
- tarefas `docs_only` e `code_small` devem apontar para cápsula;
- revisão de segurança e revisão pesada devem apontar para full_repo_review;
- live continua bloqueado nesta sprint.

## Baseline

- `factoryos_baseline_tokens=23302`
- `capsule_minimal_tokens=1198`
- savings esperado próximo de `94%`
