# Technical Spec — Factory Reports & Snapshot Hardening V0

## Escopo

Implementar um seletor central de reports e registrar um snapshot explícito do workspace no metadata da run.

## Arquivos

- `app/report_index.py`
- `app/run_workspace.py`
- `app/execution_evaluator.py`
- `app/factory_start.py`
- `app/cli.py`
- `app/panel_data.py`
- `app/templates/index.html`

## Report Index V0

`app/report_index.py` deve:

- mapear tipos mínimos:
  - `factory-starts`
  - `factory-start-live-canary`
  - `factory-loops`
  - `factory-ticks`
  - `execution-evaluations`
  - `run-handoffs`
  - `factory-state-hygiene`
  - `live-canary`
- ignorar qualquer arquivo fora de `.json`;
- ignorar temporários e arquivos inválidos;
- ordenar por timestamp de payload, fallback pelo nome e por `mtime`;
- filtrar por `run_id` usando `run_id` e `canary_run_id`;
- oferecer `list_reports`, `latest_report` e `latest_report_among`.

## Snapshot hardening

`run_workspace.py` deve:

- gravar no JSON da run:
  - `workspace_head`
  - `main_head`
  - `snapshot_at`
- expor `expected_main_head` e `expected_workspace_head` em `workspace_status` e `run_workspace_readiness`;
- marcar `needs_sync_review` quando o `main_head` mudar desde o prepare;
- marcar `blocked` quando o `workspace_head` divergir do snapshot esperado.

## Integrações

- `execution_evaluator` deve escolher source report com prioridade controlada;
- `factory_start` e loaders do painel devem consumir o seletor central quando simples;
- a CLI pode expor `report-latest` e `report-list`.

## Retenção

Política apenas documental nesta sprint:

- manter todos os reports;
- selecionar o último válido por tipo;
- não fazer delete automático nem manual como parte da feature.
