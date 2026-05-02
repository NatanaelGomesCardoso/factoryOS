# Reuse First Discovery

## Ideia

Sprint 015 Factory Tick V0

## Criado em

2026-04-30T15:09:00-03:00

## Objetivo desta etapa

Antes de criar o primeiro tick da fábrica, reaproveitar os padrões já presentes no repo para comando local simples, state machine pequena, dry-run first e reports locais com leitura segura.

## O que já existe no repo

- `app/cli.py` como adaptador de comandos locais;
- `app/run_workspace.py` com readiness e sync plan;
- `app/codex_handoff.py` com handoff e dry-run local;
- `app/panel_data.py` com snapshot read-only do painel;
- `reports/` como padrão para artifacts locais.

## Padrões avaliados

- job runner simples e síncrono;
- state machine local pequena;
- dry-run first como comportamento padrao;
- logs e reports locais como fonte de auditoria;
- tick explícito, local e sem automação contínua.

## Decisão V0

- tick síncrono;
- tick explícito;
- tick local;
- sem daemon;
- sem scheduler;
- sem paralelismo;
- sem execução live real de Codex nesta sprint.

## Por que este corte

O repo já possui os blocos necessários para decidir se uma run pode avançar: readiness, sync plan e handoff. O tick V0 apenas compõe esses passos numa orquestração auditável e grava um report próprio.

## Próximo passo

Gerar PRD, SPEC técnica e sprint JSON para o Factory Tick V0, depois implementar o comando `factory-tick`.
