# Reuse First Discovery

## Ideia

Sprint 017 Validator/Evaluator Loop V0

## Objetivo desta etapa

Transformar um report local já existente em uma decisão estruturada sem rodar Codex live novamente.

## O que já existe no repo

- `app/evaluator.py` como referência de decisão local simples;
- `app/task_runner.py` com `task-evaluate` e leitura segura de tasks;
- `app/factory_tick.py` com composição local de readiness e sync plan;
- `app/codex_handoff.py` com reports e validações de execução;
- `app/live_canary.py` com o report real da Sprint 016;
- `app/panel_data.py` e o painel read-only com leitura de reports;
- `reports/live-canary/`, `reports/run-handoffs/` e `reports/factory-ticks/` como base de auditoria;
- `task runner` e `run runner` locais já existentes.

## Padrões avaliados

- comando explícito, local e síncrono;
- reuso de report existente como fonte de verdade;
- validação segura de JSON e caminho relativo;
- decisões estruturadas para passed, failed, blocked e needs_review;
- painel read-only com link para artefato.

## Decisão V0

- evaluator síncrono;
- evaluator local;
- sem daemon;
- sem scheduler;
- sem retry automático;
- sem execução live nova de Codex.

## Por que este corte

O FactoryOS já gera reports de execução, handoff e canary. Falta um comando que leia esses artefatos e decida, de forma auditável, se uma run pode ser considerada concluída.

## Próximo passo

Gerar PRD, SPEC técnica e sprint JSON da Sprint 017 antes de implementar o evaluator e a integração no painel.
