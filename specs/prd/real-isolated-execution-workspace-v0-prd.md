# PRD - Real Isolated Execution Workspace V0

## Problema

As runs do FactoryOS existem localmente, mas o workspace ainda pode começar como diretório simples. Antes de liberar execução live do Codex, o sistema precisa de isolamento real por run.

## Objetivo

Criar um workspace real e isolado por run usando `git worktree` e branch dedicada, mantendo o live do Codex bloqueado nesta sprint.

## Não objetivos

- não executar Codex live;
- não implementar daemon;
- não implementar scheduler;
- não implementar App Server;
- não implementar MCP;
- não integrar GitHub ou Linear;
- não implementar execução paralela;
- não criar `factory-start`;
- não fazer deploy.

## Usuário

Pessoa operando o FactoryOS localmente e precisando preparar uma run com isolamento real antes de qualquer execução futura.

## Comandos esperados

- `run-workspace-prepare <run-id>`
- `run-workspace-status <run-id>`
- `run-handoff <run-id>`
- `run-execute <run-id> --dry-run`

## Segurança

- validar `run_id` e bloquear path traversal;
- exigir `git status` limpo no repo principal antes de criar o worktree;
- não apagar worktree ou branch automaticamente;
- não sobrescrever diretório populado que não seja o worktree esperado;
- não aceitar caminho absoluto vindo de JSON;
- manter execução live bloqueada.

## Critérios de pronto

- a run ganha branch dedicada local;
- o workspace real é criado como `git worktree`;
- o status do workspace pode ser consultado sem alterar nada;
- o handoff reconhece o workspace preparado;
- o painel mostra os metadados principais de workspace;
- `run-execute --dry-run` continua seguro;
- nenhuma execução live do Codex acontece.
