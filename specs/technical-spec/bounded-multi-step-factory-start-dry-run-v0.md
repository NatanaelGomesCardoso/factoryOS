# Technical Spec — Bounded Multi-Step Factory Start Dry-Run V0

## Escopo

Adicionar orquestração multi-step bounded ao `factory-start` em modo `dry-run`.

## Arquivos

- `app/factory_start.py`
- `app/cli.py`
- `app/execution_evaluator.py`
- `app/report_index.py`
- `app/panel_data.py`
- `app/templates/index.html`

## Fluxo

1. validar `run_id` quando informado;
2. validar `max_steps` entre `1` e `3`;
3. rodar `factory_state_audit` e `factory_state_plan`;
4. executar `factory-loop` V1 com `max_steps=1` uma vez por step;
5. interromper a sequência se algum step sair de `dry_run_only`;
6. persistir report consolidado com `steps[]`;
7. se `--evaluate` existir, rodar `execution_evaluate` no report do start.

## Report esperado

- `mode=dry-run`;
- `steps_requested`;
- `steps_completed`;
- `steps[]` com `step`, `loop_report`, `status`, `decision`, `executed_live`;
- `executed_live=false`;
- `evaluation_report`;
- `evaluation_decision`;
- `final_decision`.

## Limites

- síncrono;
- bounded;
- sem live;
- sem daemon;
- sem scheduler;
- sem paralelismo;
- sem criação automática de run.
