# PRD - Live Codex Canary V0

## Problema

O FactoryOS já prepara task, run, worktree e handoff, mas ainda não existe uma prova viva, mínima e explícita de que o Codex pode rodar uma única vez dentro do worktree isolado sem tocar no master, sem deploy e sem segredos.

## Objetivo

Criar e executar um canário live único, local e auditável do Codex, limitado a criar ou atualizar somente `reports/live-canary/codex-canary.txt` dentro do worktree da run canary.

## Nao objetivos

- não implementar daemon;
- não implementar scheduler;
- não implementar App Server;
- não implementar MCP;
- não integrar GitHub ou Linear;
- não implementar execução paralela;
- não criar `factory-start` ainda;
- não fazer retry loop;
- não fazer merge da branch canary no master;
- não fazer rebase;
- não fazer fetch/pull;
- não fazer deploy;
- não mexer em secrets;
- não mexer em produção.

## Usuario

Pessoa operando o FactoryOS localmente e precisando provar, de forma inofensiva e verificável, que uma execução live isolada do Codex funciona uma única vez.

## Fluxo do canário

1. criar a task canary;
2. criar a run canary;
3. preparar o worktree isolado;
4. checar readiness;
5. checar sync plan;
6. gerar handoff;
7. executar o Codex live uma única vez;
8. validar o arquivo permitido;
9. validar que o master continua intacto;
10. registrar report local final.

## Limites

- 1 execução live;
- 0 retry;
- timeout máximo de 10 minutos;
- no máximo 2 arquivos alterados;
- arquivo permitido único: `reports/live-canary/codex-canary.txt`;
- sem deploy;
- sem API paga;
- sem segredos;
- sem alteração global de configuração;
- sem push;
- sem merge para master.

## Criterios de pronto

- o canário live executa exatamente uma vez;
- o worktree isolado é preparado antes da execução;
- readiness retorna `ready`;
- sync plan retorna `already_current`;
- o report final existe e é válido;
- o arquivo permitido é o único arquivo alterado;
- o master continua limpo;
- o painel local continua funcionando.
