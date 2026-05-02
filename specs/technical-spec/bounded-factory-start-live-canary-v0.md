# SPEC Técnica - Bounded Factory Start Live Canary V0

## Comando

Adicionar suporte controlado a:

`factory-start --live --run-id <RUN_ID> --max-steps 1 --canary`

## Guardrails obrigatórios

- exigir `FACTORYOS_ENABLE_LIVE_CODEX=1`;
- exigir `--canary`;
- exigir `--run-id` explícito;
- exigir `max_steps=1`;
- exigir `run` em `running`;
- exigir `readiness=ready`;
- exigir `sync_plan=already_current`;
- exigir workspace `git worktree`.

## Execução live

- rodar somente dentro do worktree da run;
- usar:
  `codex exec --ignore-user-config --ephemeral --cd <workspace_path> --model gpt-5.4-mini -c model_reasoning_effort='"medium"' -c approval_policy='"never"' -c sandbox_mode='"danger-full-access"' "<prompt>"`
- timeout máximo de 10 minutos;
- sem retry.

## Arquivo permitido

Somente:

- `reports/factory-start-live-canary/factory-start-canary.txt`

## Pós-validação

- validar `master_head_before == master_head_after`;
- validar `changed_files` limitado ao arquivo permitido;
- validar `codex_exit_code=0`;
- registrar `no_push`, `no_deploy`, `no_paid_api`, `no_secrets`;
- salvar report em `reports/factory-start-live-canary/`;
- não fazer merge para `master`.
