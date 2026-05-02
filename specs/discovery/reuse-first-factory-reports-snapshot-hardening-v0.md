# Reuse First — Factory Reports & Snapshot Hardening V0

## Objetivo

Reduzir ruído na seleção de reports e endurecer o snapshot do workspace logo após `run-workspace-prepare`, sem apagar histórico e sem executar Codex live.

## Reuso obrigatório

- reaproveitar reports existentes em `reports/*`;
- reaproveitar loaders atuais do painel;
- reaproveitar `app.execution_evaluator`;
- reaproveitar `app.run_workspace`;
- reaproveitar `factory-start` e `factory-loop` como consumidores do report selector quando fizer sentido.

## Decisão V0

- criar um `report_index` local e simples em `app/report_index.py`;
- selecionar somente JSON válido;
- ignorar `stdout`, `stderr` e arquivos temporários;
- ordenar por timestamp de payload/nome e `mtime`;
- filtrar por `run_id` quando aplicável;
- documentar retenção, sem delete nesta sprint.

## Fora de escopo

- deletar reports;
- compactar histórico;
- daemon;
- scheduler;
- live;
- mutações pelo painel.
