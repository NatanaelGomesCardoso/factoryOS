# SPEC Tecnica - Autonomous Factory Control Plane V0

## Decisao tecnica

Documentar a control plane local-first sem introduzir automacao de execucao, daemon, scheduler, App Server ou MCP. A Sprint 009 define contrato, limites e papeis para o futuro, mas nao implementa o heartbeat ativo.

## Arquivos provaveis

- `WORKFLOW.md`
- `docs/architecture/autonomous-factory-control-plane.md`
- `specs/discovery/reuse-first-autonomous-factory-control-plane.md`
- `specs/prd/autonomous-factory-control-plane-v0-prd.md`
- `specs/sprints/009-autonomous-factory-control-plane-v0.json`
- `reports/autonomous-control-plane-v0-proof.txt`

## Modelo operacional

### Board

Usuario + ChatGPT web aprovam apenas o fechamento final: PR ou review final.

### Architect

ChatGPT web define a arquitetura, valida a direcao e revisa os marcos principais.

### Factory Manager

FactoryOS registra tasks, organiza o estado local, valida o fluxo e produz reports.

### Coder

Codex CLI executa apenas trabalho dentro dos limites locais aprovados.

### QA

Evaluator + testes locais classificam sinais, checam regressao e registram resultado.

### Archivist

Obsidian + reports guardam as decisoes, provas e resumem o estado do ciclo.

### Security Guard

Harness + gates de seguranca bloqueiam abuso, risco critico e qualquer tentativa de mover a base para superfícies proibidas.

## Budget caps

Cada future run deve carregar:

- `max_codex_runs`
- `max_retry_attempts`
- `max_changed_files`
- `max_minutes`
- `model`
- `reasoning_effort`
- `stop_on_security_risk`

### Interpretacao

- `max_codex_runs`: numero maximo de execucoes do Codex na tarefa.
- `max_retry_attempts`: numero maximo de retries antes de falhar.
- `max_changed_files`: limite de arquivos alterados por run ou por ciclo.
- `max_minutes`: teto de tempo para a execucao controlada.
- `model`: modelo permitido para a tarefa.
- `reasoning_effort`: nivel de esforco aceito.
- `stop_on_security_risk`: parada obrigatoria quando risco critico aparecer.

## Governança

### Acoes livres

- editar codigo no workspace da task;
- rodar testes locais;
- gerar reports;
- criar commits locais.

### Acoes com gate final

- PR;
- review final.

### Acoes bloqueadas sem aprovacao

- deploy;
- secrets;
- billing;
- infraestrutura publica;
- configuracao global;
- apagar dados;
- API paga.

## Fluxo futuro `factory-tick`

O heartbeat futuro deve permanecer como contrato, nao como implementacao nesta sprint.

### Sequencia prevista

1. localizar tasks `running`;
2. abrir um run;
3. chamar um executor adapter;
4. validar saida local;
5. avaliar sinais;
6. decidir `retry`, `done` ou `failed`;
7. atualizar painel e reports.

### Regras do contrato

- nao aceitar microaprovacoes no meio do ciclo;
- nao chamar Codex fora dos limites definidos;
- nao usar daemon nem scheduler nesta sprint;
- nao depender de API paga;
- nao permitir escrita fora do workspace da task;
- nao expor segredo, token ou chave em reports.

## Fora de escopo

- execucao automatica de Codex;
- daemon;
- scheduler;
- App Server;
- MCP;
- integracao GitHub/Linear;
- execucao paralela;
- deploy.

## Validacao

- `python -m json.tool specs/sprints/009-autonomous-factory-control-plane-v0.json`
- `python -m app.cli task-list`
- `TestClient` com `base_url=http://127.0.0.1` e `GET /` retornando 200
- `git diff --check`

## Nota de implementacao

Esta sprint e documental e de alinhamento operacional. Ela prepara o terreno para futuras tasks de workspace isolado, loop de execucao do Codex e gate final de PR, sem ativar nenhum desses componentes ainda.
