# SPEC Técnica - Factory Start Dry-Run V0

## Decisão

Adicionar uma camada `factory-start` acima do `factory-loop` V1, mantendo toda a execução em dry-run e produzindo report próprio.

## Fluxo

1. validar `run_id` quando informado;
2. validar `max_steps` no intervalo `1..3`;
3. executar `factory-state-audit` e `factory-state-plan`;
4. chamar `factory-loop` V1 em dry-run;
5. gravar report em `reports/factory-starts/<timestamp>-<run-token>.json`.

## Report mínimo

O report deve incluir:

- `factory_start_version = v0`
- `mode = dry-run`
- `start_id`
- `run_id`
- `max_steps`
- `steps_requested`
- `steps_completed`
- `status`
- `decision`
- `loop_report`
- `hygiene_summary`
- `executed_live = false`
- `started_at`
- `finished_at`
- `reasons`

## Guardrails

- bloquear path traversal em `run_id`;
- não usar `shell=True`;
- não executar Codex live;
- não criar daemon, scheduler ou loop infinito;
- não criar run automaticamente no fluxo padrão;
- `--live` retorna `live mode is out of scope for Factory Start Dry-Run V0.`

## Painel

Seção read-only para o último Factory Start com:

- version
- mode
- status
- decision
- max_steps
- steps_completed
- executed_live
- link para report
