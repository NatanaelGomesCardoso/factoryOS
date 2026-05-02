# Reuse First - Factory Start Capsule Mode V0

## Objetivo

Propagar a policy de cápsula para o caminho `factory-start` e para o `run-handoff`.

## Reuso desejado

- `capsule_execution_policy`
- `codex_handoff`
- `factory_start`
- `codex_context_router`
- `codex_profile`

## Hipótese

`factory-start --plan-only --cost-aware` pode informar o executor econômico sem executar live.

## Critério de decisão

- tarefas baratas usam cápsula;
- tarefas médias usam cápsula ou `repo_quiet` conforme os arquivos incluídos;
- segurança e revisão pesada ficam em `full_repo_review`;
- live permanece bloqueado.

## Saída esperada

- `run-handoff` com campos de policy;
- plano cost-aware com economia esperada;
- canário dry-run sem execução live.
