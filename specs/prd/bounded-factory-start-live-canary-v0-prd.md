# PRD - Bounded Factory Start Live Canary V0

## Problema

O `factory-start` dry-run já está pronto, mas ainda falta uma prova mínima de execução live bounded usando uma run nova e um escopo de escrita extremamente restrito.

## Objetivo

Executar exatamente um canário live do `factory-start`, com `max_steps=1`, em worktree isolado e com alteração permitida em apenas um arquivo de prova.

## Reuso primeiro

- `factory-start` V0
- `factory-loop` V1
- `live canary` V0
- `run workspace`
- `execution-evaluate`

## Regras

- `factory-start --live --run-id <run-id> --max-steps 1 --canary` é o único fluxo live permitido;
- sem `--canary`, o live deve bloquear;
- `max_steps` precisa ser exatamente `1`;
- `run_id` precisa ser explícito e válido;
- `master` deve permanecer intacto antes e depois;
- `changed_files` deve conter apenas `reports/factory-start-live-canary/factory-start-canary.txt`;
- `codex_exit_code=0` quando executado;
- sem push, deploy, API paga ou secrets.

## Critérios de pronto

- task Sprint 023 fechada como `done` ou `blocked` documentado;
- report JSON de live canary gerado;
- evaluator consegue localizar o report por `run_id` ou o bloqueio fica documentado;
- painel continua read-only e mostra o último Factory Start Live Canary;
- `git diff --check` passa.
