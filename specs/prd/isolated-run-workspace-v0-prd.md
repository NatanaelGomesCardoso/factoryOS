# PRD - Isolated Run Workspace V0

## Objetivo

Criar a primeira base local para workspaces isolados por run no FactoryOS, sem executar Codex automaticamente ainda.

## Problema

O FactoryOS ja organiza tasks e painéis, mas ainda nao possui uma area isolada por run para guardar metadata, limites e estado operacional sem depender de automacao ativa.

## Solucao V0

Implementar um ciclo local e simples:

- criar run a partir de uma task existente;
- gerar metadata JSON da run;
- criar diretório isolado por run;
- registrar budget caps;
- registrar estado da run;
- listar, mostrar, finalizar e falhar runs manualmente;
- expor a ultima run no painel se for simples e seguro.

## Decisão de arquitetura

- usar diretorios locais e metadata JSON;
- considerar `git worktree` como referencia madura;
- nao usar worktree no V0 se a complexidade não compensar;
- nao chamar Codex automaticamente;
- nao executar comandos dentro do workspace ainda;
- manter o backend como fonte de verdade;
- manter o painel read-only.

## Modelo operacional

### Criacao de run

- a run nasce vinculada a uma task existente;
- o workspace isolado e criado em `workspaces/runs/<run-id>/`;
- o JSON da run fica em `runs/running/<run-id>.json`;
- o status inicial pode ser `running` para evitar um comando extra de start.

### Estrutura de estado

- `pending` fica reservado para evolucao futura, se necessario;
- `running` representa a run ativa;
- `done` representa conclusao manual;
- `failed` representa encerramento manual com motivo registrado.

### Budget caps

Cada run carrega:

- `max_codex_runs`;
- `max_retry_attempts`;
- `max_changed_files`;
- `max_minutes`;
- `model`;
- `reasoning_effort`;
- `stop_on_security_risk`.

## Regras de segurança

- validar `run_id` e `task_id`;
- bloquear path traversal;
- nao escrever fora de `runs/` e `workspaces/runs/`;
- nao armazenar caminho absoluto se nao for necessario;
- nao apagar workspace automaticamente;
- nao limpar arquivos do usuario;
- nao executar comandos dentro do workspace;
- nao implementar chamada automatica de Codex;
- nao depender do frontend para regra critica.

## CLI esperada

- `python -m app.cli run-create <task-id>`
- `python -m app.cli run-list`
- `python -m app.cli run-show <run-id>`
- `python -m app.cli run-finish <run-id>`
- `python -m app.cli run-fail <run-id> --reason "..."`

## Critérios de pronto

- existe uma run local ligada a uma task existente;
- metadata JSON da run e valida;
- workspace isolado da run e criado;
- list/show/finish/fail funcionam;
- o painel continua funcionando;
- a ultima run aparece no painel se houver uma run valida;
- nenhuma execucao automatica de Codex foi implementada.
