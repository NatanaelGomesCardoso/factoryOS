# Symphony Alignment

## Contexto

O FactoryOS está no marco **Operational Core V0.2** e a Sprint 008 fechou com `task-evaluate` e painel exibindo o resultado da avaliação. O estudo do OpenAI Symphony mostra um modelo mais amplo de orquestração de issues para execuções isoladas de agentes.

## Decisão

O FactoryOS **não vai migrar para Symphony agora**.

O Symphony será usado como **referência de padrões**, não como dependência técnica ou operacional.

## Comparacao

### FactoryOS atual

- opera local-first;
- usa fluxo controlado por arquivos, tarefas e painel;
- validação e avaliação acontecem no próprio ambiente local;
- o objetivo imediato é reduzir acoplamento e manter previsibilidade.

### OpenAI Symphony

- foca em transformar issues em execuções isoladas de agentes;
- assume uma camada de orquestração mais explícita;
- enfatiza separação de responsabilidades entre orquestrador e executor;
- prioriza rastreabilidade de run e handoff humano.

## Conceitos reaproveitados

O FactoryOS deve absorver os seguintes padrões do Symphony:

- `WORKFLOW.md` versionado;
- workspace isolado por task;
- run metadata;
- handoff para revisão humana;
- observabilidade por run;
- separação orquestrador/executor.

## Limites atuais

O FactoryOS **não vai usar agora**:

- Linear;
- daemon always-on;
- execução paralela;
- Codex App Server;
- MCP/App SDK;
- API paga;
- workers remotos.

## Direcao

O próximo ciclo deve preparar a base para execução isolada sem importar a pilha do Symphony. A prioridade é consolidar o modelo local-first e tornar cada run auditável, reproduzível e fácil de revisar.

## Resultado esperado

FactoryOS continua simples no núcleo, mas passa a organizar a execução futura com os mesmos princípios estruturais do Symphony, sem adotar a infraestrutura dele.
