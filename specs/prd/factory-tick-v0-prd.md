# PRD - Factory Tick V0

## Problema

O FactoryOS já consegue avaliar readiness, sync plan e handoff separadamente, mas ainda falta um comando único e auditável para decidir, em um passo só, se uma run pode seguir para um caminho futuro de live.

## Objetivo

Criar um tick único, síncrono e local que receba uma run, cheque readiness, cheque sync plan, gere handoff, execute dry-run por padrão e produza um report de decisão.

## Nao objetivos

- não executar live real de Codex nesta sprint;
- não implementar daemon;
- não implementar scheduler;
- não implementar App Server;
- não implementar MCP;
- não integrar GitHub ou Linear;
- não implementar execução paralela;
- não criar `factory-start` ainda;
- não fazer deploy;
- não fazer retry loop;
- não criar PR automático.

## Usuario

Pessoa operando o FactoryOS localmente e precisando de um passo único para decidir se a run está segura para continuar em direção a uma future live.

## Fluxo do tick

1. receber `run_id`;
2. validar que a run existe;
3. validar que a run está `running`;
4. checar readiness;
5. checar sync plan;
6. bloquear se readiness não for `ready`;
7. bloquear se sync plan não for `already_current`;
8. gerar handoff local;
9. executar `run-execute --dry-run`;
10. validar o report JSON;
11. gravar report próprio do tick;
12. retornar JSON no stdout.

## Criterios de seguranca

- validar `run_id` e bloquear path traversal;
- não usar `shell=True`;
- não chamar Codex live nesta sprint;
- não usar API paga;
- não mexer em secrets;
- não alterar worktree;
- não fazer commit automático;
- não alterar o repo principal fora dos arquivos da sprint;
- manter o painel read-only.

## Criterios de pronto

- o comando `factory-tick --run-id <run-id> --dry-run` funciona;
- `factory-tick` bloqueia run inválida e path traversal;
- `factory-tick` bloqueia se a run não estiver `running`;
- `factory-tick` bloqueia se readiness não for `ready`;
- `factory-tick` bloqueia se sync plan não for `already_current`;
- o report JSON do tick é gerado em `reports/factory-ticks/`;
- o painel continua funcionando;
- não há execução live real de Codex nesta sprint.
