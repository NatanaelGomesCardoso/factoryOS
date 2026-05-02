# Reuse First Discovery

## Ideia

Sprint 018 Controlled Execution Loop V0

## Objetivo desta etapa

Conectar os blocos já existentes do FactoryOS em um loop local, explícito e síncrono, com limite pequeno de passos e dry-run por padrão, sem daemon, sem scheduler e sem live Codex.

## O que já existe no repo

- `app/task_runner.py` para tasks locais;
- `app/run_workspace.py` para run, workspace, readiness e sync plan;
- `app/codex_handoff.py` para `run-handoff` e `run-execute --dry-run`;
- `app/factory_tick.py` para compor readiness, sync plan, handoff e dry-run;
- `app/execution_evaluator.py` para avaliação estruturada de reports;
- `app/panel_data.py`, `app/web.py` e o painel read-only;
- `reports/` como base de auditoria local.

## Padrões avaliados

- reuso primeiro dos comandos locais já existentes;
- controle explícito por `run_id`;
- seleção automática somente quando houver uma única run running;
- bloqueio seguro quando readiness ou sync plan não permitirem avançar;
- report JSON auditável por loop;
- painel somente leitura.

## Decisão V0

- loop explícito;
- loop local;
- loop síncrono;
- max_steps pequeno;
- sem daemon;
- sem scheduler;
- sem live;
- sem retry automático.

## Por que este corte

O FactoryOS já sabe preparar workspace, avaliar readiness, gerar sync plan, executar tick seco e avaliar report. Falta uma orquestração local que amarre essas peças em um comando único, auditável e com saída estável.

## Próximo passo

Gerar PRD, SPEC técnica, sprint JSON e implementar `factory-loop` em cima dos blocos existentes.
