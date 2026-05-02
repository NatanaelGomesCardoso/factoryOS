# Reuse First Discovery

## Ideia

Autonomous Factory Control Plane V0

## Objetivo desta etapa

Decidir quais padroes maduros podem ser reaproveitados para organizar o FactoryOS como control plane local de agentes, sem migrar a base para uma pilha externa.

## Contexto

- O FactoryOS esta no marco Operational Core V0.2.
- A Sprint 008 fechou com `task-evaluate` e painel exibindo avaliacao de task.
- Symphony ja foi estudado como blueprint de workflow e workspace.
- Paperclip entra agora como referencia para org chart, budgets, governance e heartbeats.

## O que pesquisar

- padroes de org chart para agentes;
- budgets e limites operacionais;
- governance de tarefas e runs;
- heartbeats e tick loops;
- workspaces isolados;
- handoff humano final;
- rastreabilidade local;
- repositorios e docs que sirvam como referencia, nao como dependencia.

## Critérios de avaliação

Para cada padrao encontrado, avaliar:

- maturidade;
- simplicidade;
- compatibilidade com local-first;
- dependencia externa;
- custo;
- risco de seguranca;
- facilidade de auditoria;
- adequacao ao fluxo sem microaprovacoes.

## Decisão de reuse

- [ ] usar pronto;
- [ ] adaptar;
- [x] usar como referencia;
- [ ] criar pequeno customizado;
- [ ] adiar.

## Justificativa

O FactoryOS ainda esta consolidando o core operacional local. O valor dos estudos de Symphony e Paperclip esta nos padroes de organizacao e governanca, nao na adocao da stack deles. Reaproveitar a linguagem operacional reduz retrabalho e evita dependencia desnecessaria.

## Impacto esperado no PRD/SPEC

- definir o Board, Architect, Factory Manager, Coder, QA, Archivist e Security Guard;
- explicitar budget caps;
- separar acoes livres, acoes com gate final e acoes bloqueadas;
- descrever o heartbeat futuro `factory-tick`;
- manter fora de escopo a execucao automatica de Codex e o daemon.

## Proximo passo

Gerar o PRD, a SPEC tecnica e o Sprint JSON da Sprint 009 com o modelo de control plane local-first.
