# Reuse First Discovery

## Ideia

Criar `factory-start` V0 em modo dry-run, explícito e bounded, reaproveitando o `factory-loop` V1 sem liberar live.

## Reaproveitamento obrigatório

- `factory-loop` V1;
- `factory-state-audit` e `factory-state-plan`;
- `task runner`;
- `run workspace`;
- `run-workspace-readiness`;
- `run-workspace-sync-plan`;
- reports existentes.

## Decisão V0

`factory-start` continua:

- explícito;
- local;
- síncrono;
- bounded;
- sem daemon;
- sem scheduler;
- sem live;
- sem paralelismo.

## Restrições

- não criar run automaticamente no fluxo padrão;
- sem Codex live;
- `max_steps` obrigatório e pequeno;
- report JSON auditável em `reports/factory-starts/`.
