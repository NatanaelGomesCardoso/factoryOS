# Technical Spec — Factory Long Run Dry-Run Planner V0

## Módulo

`app/long_run_planner.py` resolve a run, coleta sinais existentes e grava um plano único em JSON.

## Entradas

- `run_id` opcional;
- `target_minutes` entre 15 e 60;
- `max_steps` entre 1 e 6;
- `live` bloqueado explicitamente.

## Saída

O report inclui:

- `planner_status=dry_run_plan_only`;
- `allowed_to_execute_live=false`;
- `required_manual_review=true`;
- `route_contract`;
- resumo de perfil/contexto/higiene;
- `steps[]`, `risks[]`, `blockers[]`, `gates[]`.

## Seleção

- `--run-id`: usa a run explícita, desde que esteja em `running`;
- sem `--run-id`: auto seleciona apenas uma run elegível com `readiness=ready` e `sync_plan` seguro;
- zero elegíveis: `blocked`;
- múltiplas: `needs_review`.

## Segurança

Somente leitura e geração de report. Nenhum live, nenhum cleanup e nenhum push/deploy.
