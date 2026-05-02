# Reuse First Discovery

## Ideia

Factory State Hygiene V0 para auditar tasks e runs antigas em `running`, gerar um plano conservador de fechamento e reduzir ambiguidade para seleção automática futura.

## Criado em

2026-04-30

## Objetivo desta etapa

Antes de criar uma limpeza mais agressiva, reaproveitar o que já existe no FactoryOS:

- `task-list` para ler a fila de tasks;
- `run-list` para ler a fila de runs;
- `task-show` e `run-show` para validar detalhes;
- `task-finish` e `run-finish` para fechar apenas o que estiver claramente seguro;
- reports e proofs já gerados nas sprints anteriores.

## Reaproveitamento primeiro

O V0 deve partir do que já existe e não inventar um novo modelo de estado:

- tasks e runs continuam sendo a fonte de verdade local;
- reports antigos são prova suficiente quando o fechamento já estiver documentado;
- o painel continua read-only;
- nada deve ser apagado;
- worktrees não devem ser removidos;
- não existe Codex live nesta sprint.

## Decisão V0

Auditoria local, plano explícito e aplicação conservadora.

Se houver dúvida, a decisão é `needs_review`.

## Próximo passo

Gerar:

1. PRD;
2. SPEC técnica;
3. sprint JSON;
4. implementação local.
