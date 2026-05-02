# Reuse First Discovery

## Ideia

Sprint 016 Live Codex Canary V0

## Criado em

2026-04-30T18:37:00-03:00

## Objetivo desta etapa

Antes de expor a primeira execução live do Codex, reaproveitar os blocos que já existem no FactoryOS para preparar task, run, worktree, readiness, sync plan, handoff e reports locais.

## O que já existe no repo

- `app/task_runner.py` para task local;
- `app/run_workspace.py` para run, worktree, readiness e sync plan;
- `app/codex_handoff.py` para handoff e execução controlada;
- `app/live_canary.py` para a orquestração específica do canário;
- `app/panel_data.py` e o painel para leitura local;
- `reports/` como trilha de prova local.

## Padrões reaproveitados

- task runner local;
- run workspace isolado por run;
- readiness gate local;
- sync plan already_current;
- handoff explícito;
- execução live única e sem retry;
- reports locais como fonte de auditoria.

## Decisão V0

- canário live único;
- explícito;
- local;
- isolado;
- sem loop;
- sem retry;
- sem fan-out;
- sem automação contínua.

## Por que este corte

O FactoryOS já sabe preparar contexto e reportar o estado da run. A Sprint 016 só precisa empacotar uma execução live mínima, rastreável e restringida a um único arquivo permitido.

## Próximo passo

Gerar PRD, SPEC técnica, sprint JSON e o fluxo final de canário live.
