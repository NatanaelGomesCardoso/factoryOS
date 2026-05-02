# PRD - Factory Start Dry-Run V0

## Problema

O FactoryOS já consegue avaliar e executar um loop controlado em dry-run, mas ainda falta um comando de início explícito, mais próximo do fluxo operacional real da fábrica.

## Objetivo

Entregar `factory-start` V0 em modo dry-run, usando o Controlled Execution Loop V1, sem criar daemon, scheduler ou live Codex.

## Reuso primeiro

- `factory-loop` V1
- `factory-state-audit`
- `factory-state-plan`
- task runner
- run workspace
- readiness/sync plan
- reports locais

## Regras V0

- `factory-start --dry-run --max-steps 1` usa auditoria/planejamento de state antes de decidir;
- sem `--run-id`, seleciona automaticamente apenas quando houver exatamente uma run elegível;
- zero elegíveis retorna `blocked`;
- mais de uma elegível retorna `needs_review`;
- `factory-start --dry-run --run-id <run-id> --max-steps 1` mantém o fluxo explícito;
- `factory-start --live` fica bloqueado com erro claro;
- `max_steps` aceito apenas entre 1 e 3;
- report JSON mínimo em `reports/factory-starts/`.

## Critérios de pronto

- o comando funciona com `--run-id`;
- o comportamento sem `--run-id` é seguro;
- `executed_live=false` em todos os cenários da sprint;
- o painel mostra o último Factory Start em modo read-only;
- nenhuma run é criada automaticamente pelo comando padrão.
