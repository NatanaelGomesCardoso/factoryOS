# Technical Spec - Cheap Task Factory E2E Gate V0

## Componentes

- `app/capsule_execution_policy.py`
- `app/codex_context_capsule.py`
- `app/codex_capsule_execution.py`
- `app/cheap_task_factory_e2e.py`
- `app/cli.py`

## Comandos

- `cheap-task-factory-e2e --category docs_only --label <LABEL> --dry-run`
- `cheap-task-factory-e2e --category docs_only --label <LABEL> --execute-canary`

## Fluxo

- policy escolhe `capsule`;
- cria a cápsula;
- executa o canário;
- gera diff;
- gera export-plan;
- normaliza o status final;
- consolida report compacto.

