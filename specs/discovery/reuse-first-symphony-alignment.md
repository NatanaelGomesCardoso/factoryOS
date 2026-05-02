# Reuse First Discovery

## Ideia

Alinhamento FactoryOS com padrões do OpenAI Symphony

## Objetivo desta etapa

Decidir o que reaproveitar do estudo do Symphony sem migrar a arquitetura do FactoryOS.

## Responsabilidade

- ChatGPT: comparar, decidir e registrar a direção.
- FactoryOS: manter o fluxo local-first e documentado.
- Codex: não deve receber uma ordem de migração completa; deve executar somente as próximas etapas aprovadas.

## O que existe hoje no FactoryOS

- fluxo local-first;
- `task-evaluate` com saída registrada;
- painel read-only mostrando o resultado da avaliação;
- organização por specs, sprints e discovery;
- separação entre decisão e execução local.

## O que o Symphony acrescenta como referência

- `WORKFLOW.md` versionado;
- workspace isolado por task;
- run metadata;
- handoff explícito para revisão humana;
- observabilidade por run;
- separação clara entre orquestrador e executor.

## Decisão final

- [ ] migrar para Symphony;
- [ ] adotar como dependência;
- [x] usar como referência;
- [ ] adiar;

## Justificativa

O FactoryOS ainda está consolidando o core operacional local. Migrar agora aumentaria a superfície de integração, criaria dependência desnecessária e desviaria o foco do modelo local-first. O valor do Symphony está nos padrões de organização, não na adoção da stack.

## O que nao entra agora

- Linear;
- daemon always-on;
- execução paralela;
- Codex App Server;
- MCP/App SDK;
- API paga;
- workers remotos.

## Próximos passos sugeridos

- Sprint 009: Symphony Alignment / Execution Prep V0;
- Sprint 010: Isolated Workspace V0;
- Sprint 011: Codex Execution Handoff V0.

## Impacto esperado

As próximas entregas devem preparar o FactoryOS para runs mais isoladas, com metadata de execução e handoff claro, sem abandonar o controle local-first.
