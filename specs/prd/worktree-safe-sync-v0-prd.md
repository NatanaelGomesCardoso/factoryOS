# PRD - Worktree Safe Sync V0

## Problema

O FactoryOS já consegue identificar quando um worktree por run está fora de sincronização, mas ainda falta um caminho local seguro para alinhar esse worktree com o `main` quando o fast-forward for realmente possível.

## Objetivo

Criar um plano e uma aplicação segura de fast-forward para worktree por run, sem auto-merge, sem rebase e sem correção automática de conflitos.

## Nao objetivos

- não executar Codex live;
- não implementar daemon;
- não implementar scheduler;
- não implementar App Server;
- não implementar MCP;
- não integrar GitHub ou Linear;
- não implementar execução paralela;
- não criar `factory-start`;
- não fazer deploy;
- não fazer fetch, pull, merge com commit ou rebase automático.

## Usuario

Pessoa operando o FactoryOS localmente e precisando decidir se a run pode ser sincronizada com segurança antes de qualquer live futura.

## Comandos esperados

- `run-workspace-sync-plan <run-id>`
- `run-workspace-sync-apply <run-id>`
- `run-workspace-readiness <run-id>`
- `run-handoff <run-id>`
- `run-execute <run-id> --dry-run`

## Guardrails

- validar `run_id` e bloquear path traversal;
- usar Git como fonte de verdade para `status`, branch, `HEAD` e `worktree list`;
- considerar sync local seguro só quando `workspace_head` for ancestral de `main_head`;
- bloquear se o workspace não for worktree real;
- bloquear se a branch estiver errada;
- bloquear se houver sujeira;
- bloquear se houver divergência real;
- bloquear se `main_head` ou `workspace_head` não puderem ser lidos;
- não resolver conflito automaticamente;
- não alterar o repo principal.

## Criterios de pronto

- o CLI `run-workspace-sync-plan` retorna um JSON estruturado com status seguro;
- o CLI `run-workspace-sync-apply` aplica fast-forward somente quando o plano permitir;
- o readiness da run volta a `ready` após sync bem-sucedido;
- o handoff e o dry-run carregam o readiness atualizado;
- o painel local mostra o estado do plano de sync ou o readiness atualizado;
- nenhuma execução live do Codex acontece nesta sprint.
