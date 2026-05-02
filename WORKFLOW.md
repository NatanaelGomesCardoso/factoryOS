# FactoryOS Workflow

## Proposito

Definir o fluxo versionado do FactoryOS para tarefas autonomas com controle local, sem microaprovacoes e sem automacao de execucao ainda.

## Ciclo operacional

1. ChatGPT faz discovery e define o que vale reaproveitar.
2. ChatGPT produz PRD, SPEC tecnica e Sprint JSON.
3. FactoryOS registra a sprint como task local.
4. FactoryOS move a task para `running` quando o planejamento entra em vigencia.
5. Coder executa apenas o que estiver dentro do limite aprovado.
6. QA valida com evaluator, testes e checagens locais.
7. Archivist registra o resultado em reports e memoria duravel.
8. Board faz review final apenas no PR ou fechamento.

## Regras de operacao

- nao aprovar microetapas;
- nao depender de API paga;
- nao chamar Codex a partir do app;
- nao executar daemon ou scheduler nesta fase;
- nao usar paralelo como requisito do fluxo;
- nao confiar no frontend para regra critica;
- manter o caminho local-first.

## Papéis

- Board: usuario + ChatGPT web.
- Architect: ChatGPT web.
- Factory Manager: FactoryOS.
- Coder: Codex CLI.
- QA: evaluator + testes.
- Archivist: Obsidian + reports.
- Security Guard: harness + gates de seguranca.

## Limites de execucao

Antes de qualquer run futura, a control plane deve carregar:

- budget caps;
- escopo da task;
- limite de retry;
- limite de mudancas;
- limite de tempo;
- criterio de parada por risco.

## Handoff

O handoff final acontece no review de PR ou na revisao final do pacote. O fluxo nao exige aprovacao humana para cada microacao interna do runner.
