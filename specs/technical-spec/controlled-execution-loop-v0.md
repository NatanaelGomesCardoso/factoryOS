# SPEC Técnica - Controlled Execution Loop V0

## Comando esperado

`factory-loop --run-id <run-id> --max-steps 1 --dry-run`

## Seleção de run

- aceitar `--run-id` explícito;
- validar o identificador com bloqueio de path traversal;
- exigir que a run exista;
- preferir run em `running`;
- quando `--run-id` não for informado, selecionar automaticamente apenas se houver exatamente uma run `running`;
- quando houver mais de uma run `running`, retornar `needs_review` com lista curta e pedir `--run-id` explícito;
- quando não houver run `running`, retornar `blocked`.

## max_steps

- default: `1`;
- limite V0 pequeno;
- rejeitar valores menores que 1;
- rejeitar valores acima do limite pequeno definido pela implementação.

## Pré-checagens

1. run existe;
2. run está `running`;
3. workspace readiness é `ready`;
4. sync plan é `already_current`.

## Ações por step

1. executar um tick seco explícito;
2. reutilizar `factory-tick`;
3. reaproveitar `run-handoff` e `run-execute --dry-run` indiretamente pelo tick existente;
4. tentar avaliar o report gerado;
5. registrar o report do loop;
6. retornar JSON no stdout.

## Report do loop

O report precisa incluir, no mínimo:

- `ok`;
- `mode`;
- `loop_id`;
- `run_id`;
- `task_id`;
- `max_steps`;
- `steps_executed`;
- `started_at`;
- `finished_at`;
- `status`;
- `decision`;
- `readiness_status`;
- `sync_plan_status`;
- `factory_tick_report`;
- `evaluation_report`;
- `executed_live`;
- `closed`;
- `reasons`.

## Decisões possíveis

- `dry_run_only`;
- `blocked`;
- `failed`;
- `needs_review`;
- `passed` com cautela e somente se houver evidência suficiente.

## Fechamento de run/task em V0

- não fechar run/task automaticamente por padrão;
- manter `executed_live=false`;
- manter o fluxo local e síncrono;
- se uma proteção explícita de fechamento em dry-run já existir e for chamada, ela precisa continuar segura e auditável;
- o estado normal da sprint é terminar em `dry_run_only` ou `needs_review`.

## Fora de escopo

- daemon;
- scheduler;
- retry automático;
- factory-start;
- live Codex;
- execução paralela;
- App Server;
- MCP;
- integração GitHub/Linear;
- deploy;
- merge automático;
- rebase;
- fetch/pull.
