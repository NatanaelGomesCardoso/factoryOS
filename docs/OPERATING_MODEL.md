# Modelo Operacional do FactoryOS

## Fluxo macro

1. ChatGPT conduz discovery.
2. ChatGPT gera PRD, SPEC e Sprint JSON.
3. FactoryOS quebra o trabalho em tarefas pequenas.
4. Roteador local decide se precisa de Codex.
5. Codex executa apenas tarefas reais de código.
6. Sensores validam com Git, testes, harness e Playwright.
7. Evaluator decide: passou, corrigir, escalar ou parar.
8. ChatGPT revisa marcos grandes.

## Modos de execução

- local_only: Python, templates ou Ollama resolvem.
- codex_needed: precisa Codex para código/testes.
- human_review: precisa revisão humana/ChatGPT antes.
