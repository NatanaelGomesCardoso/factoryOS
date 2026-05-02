# PRD - Autonomous Factory Control Plane V0

## Objetivo

Estruturar o FactoryOS como uma control plane local-first para operacao futura de agentes, com org chart, goals, budgets, governance e heartbeats como linguagem de controle, sem implementar execucao automatica ainda.

## Problema

O FactoryOS ja registra tasks, avalia sinais e mostra o resultado no painel, mas ainda nao possui um modelo operacional explicito para organizar quem decide, quem executa, quais limites valem e quando um ciclo futuro deve parar.

## Solucao V0

Criar a base conceitual e documental da control plane:

- Symphony entra apenas como blueprint de workflow, workspace e handoff;
- Paperclip entra como referencia para org chart, budgets, governance e heartbeats;
- FactoryOS permanece local-first, sem API paga, sem daemon e sem scheduler;
- o usuario nao aprova microetapas;
- a aprovacao humana fica para PR ou review final.

## Comparacao

- Symphony = issue/workspace/orchestration blueprint.
- Paperclip = control plane de empresa de agentes: org chart, budgets, governance, heartbeats.
- FactoryOS = versao local-first, sem API paga, sem daemon ainda, com task runner/evaluator/painel/Codex CLI.

## Padrão operacional desejado

- o usuario nao aprova microetapas;
- o usuario aprova apenas PR/final review;
- ChatGPT web atua como arquiteto e revisor final;
- Codex CLI executa codigo autonomamente dentro de limites;
- FactoryOS orquestra, registra e valida;
- o fluxo continua local-first.

## Papéis

- Board: usuario + ChatGPT web;
- Architect: ChatGPT web;
- Factory Manager: FactoryOS;
- Coder: Codex CLI;
- QA: evaluator + testes;
- Archivist: Obsidian + reports;
- Security Guard: security gate + harness.

## Budget caps

O control plane futuro deve operar com:

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

Esse comportamento e propositalmente futuro e fora desta sprint.

## Fora de escopo

- execucao automatica de Codex;
- daemon;
- scheduler;
- App Server;
- MCP;
- integracao GitHub/Linear;
- execucao paralela;
- deploy.

## Regras de produto

- nenhuma microaprovação deve travar o fluxo;
- os limites de budget precisam ser visiveis e auditaveis;
- o fluxo precisa continuar local-first;
- os estados devem permanecer rastreaveis em tasks, reports e painel;
- nenhuma regra critica pode depender apenas do frontend.

## Segurança

- nao registrar segredos, tokens ou chaves;
- nao expor caminhos absolutos desnecessarios;
- nao introduzir dependencia externa paga;
- nao tratar o frontend como fonte de verdade;
- parar em `stop_on_security_risk` quando houver risco critico.

## Criterios de pronto

- existe documentacao do control plane local-first;
- roles, budgets e governance estao descritos;
- o heartbeat futuro `factory-tick` esta especificado;
- o escopo fora de sprint esta explicito;
- nenhuma execucao automatica de Codex foi implementada.
