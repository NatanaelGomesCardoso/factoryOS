# PRD - Validator/Evaluator Loop V0

## Problema

O FactoryOS já produz reports locais de handoff, tick e live canary, mas ainda não existe um comando único para transformar um report em uma decisão final estruturada.

## Objetivo

Criar um loop local, síncrono e explícito que avalie um report existente e produza uma decisão `passed`, `failed`, `blocked` ou `needs_review`.

## Não objetivos

- não executar Codex live nesta sprint;
- não implementar daemon;
- não implementar scheduler;
- não implementar App Server;
- não implementar MCP;
- não integrar GitHub ou Linear;
- não implementar execução paralela;
- não criar `factory-start` ainda;
- não fazer deploy;
- não fazer retry loop automático;
- não fazer merge automático.

## Usuário

Pessoa operando o FactoryOS localmente e precisando decidir se uma execução já reportada pode ser considerada concluída com segurança.

## Fluxo

1. receber `run_id` ou `report_path`;
2. localizar ou abrir o report;
3. validar que o JSON existe e é válido;
4. checar evidências de execução e segurança;
5. rodar validações locais de Python e painel;
6. produzir um evaluation report JSON;
7. opcionalmente fechar run/task apenas se a decisão for `passed`.

## Decisões possíveis

- `passed`: todos os checks críticos verdadeiros;
- `failed`: execução falhou, houve alteração proibida, `master` mudou ou `codex_exit_code != 0`;
- `blocked`: report ausente, JSON inválido, caminho inseguro, run inexistente ou risco de segurança impeditivo;
- `needs_review`: dados insuficientes para decidir automaticamente.

## Critérios de pronto

- o comando `execution-evaluate --run-id <run-id>` funciona;
- o comando `execution-evaluate --report <relative-report-path>` funciona;
- path traversal é bloqueado;
- o evaluation report JSON é gravado em `reports/execution-evaluations/`;
- a decisão para o live canary da Sprint 016 é `passed`;
- o painel continua read-only;
- nenhuma execução live nova de Codex é feita.
