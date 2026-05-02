# FactoryOS Roadmap

## Marco atual

**Operational Core V0.2**

## Situação

- Sprint 008 foi fechada com `task-evaluate` e painel mostrando o resultado da avaliação;
- o core local já consegue registrar e expor o resultado da execução;
- a próxima evolução deve aumentar isolamento, rastreabilidade e governança, sem migrar a base para uma plataforma externa.

## Direcao

O FactoryOS continua **local-first**.

O OpenAI Symphony entra apenas como **blueprint arquitetural** para workflow, workspace, run metadata e handoff.

O Paperclip entra como **referência de control plane de agentes** para org chart, budgets, governance e heartbeats.

## Sprints sugeridos

### Sprint 009

**Autonomous Factory Control Plane V0**

- definir org chart, goals, budgets, governance e heartbeats como linguagem operacional;
- documentar os papéis Board, Architect, Factory Manager, Coder, QA, Archivist e Security Guard;
- explicitar o heartbeat futuro `factory-tick`;
- manter a revisão humana apenas no PR ou final review.

### Sprint 010

**Isolated Run Workspace V0**

- preparar workspace isolado por task;
- manter artefatos por run em espaço separado;
- preservar rastreabilidade local;
- reforçar limites de budget por run.

### Sprint 011

**Codex Autonomous Execution Loop V0**

- formalizar o handoff entre decisão e execução;
- reforçar observabilidade por run;
- manter o executor desacoplado da camada de orquestração;
- validar execução dentro dos budgets definidos.

### Sprint 012

**PR Review Gate V0**

- consolidar o gate final humano;
- reforçar o review como ponto de aprovação externa;
- manter o fluxo sem microaprovacoes;
- registrar o fechamento auditavel da sprint.

## Fora do escopo por enquanto

- Linear;
- daemon always-on;
- execução paralela;
- Codex App Server;
- MCP/App SDK;
- API paga;
- workers remotos.

## Regra de progresso

Cada sprint futura deve preservar o modelo local-first e adicionar apenas os padrões necessários para aproximar o FactoryOS da disciplina operacional observada no Symphony, sem virar dependência dele.
