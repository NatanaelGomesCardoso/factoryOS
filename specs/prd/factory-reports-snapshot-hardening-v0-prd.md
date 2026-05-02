# PRD — Factory Reports & Snapshot Hardening V0

## Problema

O FactoryOS já gera vários reports por sprint, run e validação. Hoje cada consumidor procura o “último” report por conta própria, o que aumenta o risco de pegar arquivos intermediários ou ruidosos. Em paralelo, o snapshot do workspace logo após `run-workspace-prepare` pode ficar pouco explícito para `status`, `readiness` e `sync-plan`.

## Objetivo

Criar uma base local, auditável e conservadora para:

- localizar o report mais recente e válido por tipo;
- reaproveitar essa seleção em pontos críticos;
- registrar no metadata da run o snapshot esperado do workspace;
- retornar bloqueio claro quando houver drift logo após o prepare.

## Requisitos

1. O sistema deve listar reports por tipo usando um índice local.
2. O índice deve ignorar `stdout`, `stderr`, temporários e JSON inválido.
3. O índice deve permitir filtro por `run_id`.
4. O painel deve continuar read-only.
5. `run-workspace-prepare` deve registrar `workspace_kind`, `workspace_branch`, `workspace_state`, `workspace_head`, `main_head` e `snapshot_at`.
6. `run-workspace-status` e `run-workspace-readiness` devem expor o snapshot esperado.
7. Se o `main_head` mudar após o prepare, a resposta deve bloquear ou pedir sync review com razão clara.

## Não objetivos

- apagar reports;
- compactar histórico;
- rodar live;
- remover worktrees.
