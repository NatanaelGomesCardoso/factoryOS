# Reuse First Discovery

## Ideia

Executar um canário live bounded do `factory-start`, limitado a `max_steps=1`, nova run e um único arquivo permitido dentro de worktree isolado.

## Reaproveitamento obrigatório

- `factory-start` V0;
- `factory-loop` V1;
- `live canary` V0;
- `run workspace`;
- `execution-evaluate`;
- reports locais.

## Decisão

Live canary:

- bounded;
- `max_steps=1`;
- nova task/run/worktree;
- arquivo permitido único;
- sem tocar em `master`;
- sem merge;
- sem push;
- sem deploy;
- sem API paga;
- sem secrets.

## Restrições

- exigir `FACTORYOS_ENABLE_LIVE_CODEX=1`;
- exigir `--canary`;
- exigir `--run-id` explícito;
- bloquear qualquer alteração fora de `reports/factory-start-live-canary/factory-start-canary.txt`.
