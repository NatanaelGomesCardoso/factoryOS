# PRD - Worktree Sync & Readiness Gate V0

## Problema

O FactoryOS ja cria worktrees reais por run, mas ainda precisa de um gate local claro antes de qualquer execucao live futura. Sem isso, um workspace sujo, fora do branch ou atrasado em relacao ao repo principal pode parecer pronto.

## Objetivo

Criar um gate de readiness local para worktrees por run, com decisao observavel e sem sincronizacao automatica.

## Nao objetivos

- nao executar Codex live;
- nao implementar daemon;
- nao implementar scheduler;
- nao implementar App Server;
- nao implementar MCP;
- nao integrar GitHub ou Linear;
- nao implementar execucao paralela;
- nao criar `factory-start`;
- nao fazer deploy;
- nao fazer merge ou rebase automatico.

## Usuario

Pessoa operando o FactoryOS localmente e precisando saber se a run esta pronta para live futura sem arriscar o estado do workspace.

## Comandos esperados

- `run-workspace-readiness <run-id>`
- `run-workspace-status <run-id>`
- `run-handoff <run-id>`
- `run-execute <run-id> --dry-run`

## Seguranca e guardrails

- validar `run_id` e bloquear path traversal;
- exigir run existente;
- usar Git como fonte de verdade para `status`, branch, HEAD e worktree;
- bloquear quando o workspace nao for um git worktree real;
- bloquear quando o branch estiver errado;
- bloquear quando o workspace estiver sujo;
- marcar `needs_sync_review` quando o HEAD do worktree divergir do HEAD principal;
- manter `ready` apenas quando o workspace estiver limpo, no branch esperado e com HEAD igual ao repo principal;
- nao fazer fetch, pull, merge ou rebase automaticos;
- nao alterar branch ou workspace.

## Criterios de pronto

- o CLI `run-workspace-readiness` retorna um JSON estruturado;
- o status diferenciado aparece como `ready`, `blocked` ou `needs_sync_review`;
- o handoff e o dry-run carregam `readiness_status`;
- o painel local mostra o readiness atual;
- nenhuma execucao live do Codex acontece nesta sprint.
