# Autonomous Factory Control Plane

## Contexto

O FactoryOS esta no marco **Operational Core V0.2**. A Sprint 008 fechou o ciclo de `task-evaluate` com o painel exibindo a avaliacao da task. A Sprint 009 nao introduz automacao de execucao; ela define a control plane local que vai organizar o que ja existe e o que virá depois.

## Comparacao de referencia

- Symphony = issue/workspace/orchestration blueprint.
- Paperclip = control plane de empresa de agentes: org chart, budgets, governance, heartbeats.
- FactoryOS = versao local-first, sem API paga, sem daemon ainda, com task runner/evaluator/painel/Codex CLI.

## Decisao

O FactoryOS vai adotar os padroes de controle do Paperclip como linguagem de operacao e os padroes de workflow do Symphony como blueprint arquitetural, sem virar dependencia de nenhuma dessas camadas.

## Padrão operacional desejado

- o usuario nao aprova microetapas;
- o usuario aprova apenas PR ou final review;
- ChatGPT web atua como arquiteto e revisor final;
- Codex executa codigo autonomamente dentro de limites;
- FactoryOS orquestra, registra e valida;
- o fluxo local continua local-first e sem API paga.

## Papéis

- Board: usuario + ChatGPT web.
- Architect: ChatGPT web.
- Factory Manager: FactoryOS.
- Coder: Codex CLI.
- QA: evaluator + testes.
- Archivist: Obsidian + reports.
- Security Guard: security gate + harness.

## Budget caps

Cada run futuro deve carregar limites claros:

- `max_codex_runs`;
- `max_retry_attempts`;
- `max_changed_files`;
- `max_minutes`;
- `model`;
- `reasoning_effort`;
- `stop_on_security_risk`.

## Governança

### Ações livres

- editar codigo no workspace da task;
- rodar testes locais;
- gerar reports;
- criar commits locais.

### Ações com gate final

- PR;
- review final.

### Ações bloqueadas sem aprovacao

- deploy;
- secrets;
- billing;
- infraestrutura publica;
- configuracao global;
- apagar dados;
- API paga.

## Heartbeat futuro

O comando futuro `factory-tick` deve:

1. checar task `running`;
2. criar run;
3. chamar executor adapter;
4. validar;
5. avaliar;
6. decidir `retry`, `done` ou `failed`;
7. atualizar o painel.

Esse contrato e futuro. Ele nao existe nesta sprint.

## Fora de escopo da Sprint 009

- execucao automatica de Codex;
- daemon;
- scheduler;
- App Server;
- MCP;
- integracao GitHub/Linear;
- execucao paralela;
- deploy.

## Resultado esperado

A Sprint 009 cria o modelo conceitual e documental da control plane. A base continua simples no nucleo e passa a expor org chart, budgets, governance e heartbeat como regras de operacao, nao como automacao ativa.
