# PRD - Controlled Execution Loop V0

## Problema

O FactoryOS já possui task runner, run runner, readiness, sync plan, factory tick e evaluator, mas ainda não existe um comando único para executar um passo controlado da fábrica em dry-run e registrar a decisão resultante.

## Objetivo

Criar um loop local, síncrono e explícito que execute no máximo poucos passos, em dry-run por padrão, verificando readiness, sync plan, factory tick e avaliação final, sem live Codex, sem daemon e sem scheduler.

## Não objetivos

- não executar Codex live nesta sprint;
- não implementar daemon;
- não implementar scheduler;
- não implementar App Server;
- não implementar MCP;
- não integrar GitHub ou Linear;
- não implementar execução paralela;
- não criar `factory-start` ainda;
- não fazer retry loop automático;
- não fazer deploy;
- não fazer merge automático;
- não fazer fetch ou pull;
- não fazer rebase.

## Usuário

Pessoa operando o FactoryOS localmente e precisando de um comando simples para verificar se uma run em andamento está pronta para seguir, sem rodar execução live.

## Fluxo do loop

1. receber `run_id` ou selecionar uma única run `running`;
2. validar o `run_id` e bloquear path traversal;
3. exigir que a run exista;
4. preferir runs em `running`;
5. checar readiness;
6. checar sync plan;
7. executar `factory-tick --dry-run`;
8. tentar avaliar o report gerado;
9. gravar report do loop em `reports/factory-loops/`;
10. retornar JSON no stdout.

## Decisões possíveis

- `dry_run_only`: o caminho seco foi executado com sucesso;
- `blocked`: uma pré-condição falhou;
- `failed`: validação local ou orquestração falhou;
- `needs_review`: o caminho seco passou, mas ainda exige revisão humana;
- `passed`: usar com cautela apenas se houver evidência suficiente, sem live nova.

## Limites

- `max_steps` pequeno, com valor padrão 1;
- sem mutação de worktree;
- sem live Codex;
- sem retry automático;
- sem execução paralela;
- sem fechamento automático de run/task no V0, exceto se houver proteção explícita já prevista e chamada em dry-run.

## Critérios de pronto

- `factory-loop --run-id <run-id> --max-steps 1 --dry-run` funciona;
- `factory-loop --max-steps 1 --dry-run` seleciona automaticamente apenas quando houver uma única run running;
- `factory-loop --live` é bloqueado com erro claro;
- path traversal é bloqueado;
- report JSON é gerado em `reports/factory-loops/`;
- `executed_live` permanece `false`;
- o painel continua read-only;
- nenhuma execução live nova de Codex acontece.
