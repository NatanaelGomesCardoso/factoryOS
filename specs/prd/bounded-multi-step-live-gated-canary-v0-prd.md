# PRD — Bounded Multi-Step Live-Gated Canary V0

## Problema

O `factory-start` já possui canário live mínimo, mas ainda não existe gate rígido para um fluxo multi-step pequeno com dois arquivos canary permitidos.

## Objetivo

Executar um canário live multi-step bounded, com no máximo `2` steps, `run_id` explícito, worktree isolado, avaliação obrigatória e `master` intacto.

## Requisitos

1. O comando válido deve ser `FACTORYOS_ENABLE_LIVE_CODEX=1 ... factory-start --live --canary --evaluate --run-id <RUN_ID> --max-steps 2`.
2. Sem `--canary`, sem `--evaluate`, sem `run_id` ou sem env var o fluxo deve bloquear.
3. `max_steps` maior que `2` deve bloquear.
4. O live só pode tocar os arquivos canary permitidos.
5. O report final deve registrar `steps[]`, `changed_files`, `codex_exit_codes` e heads antes/depois.
6. `final_decision=passed` só pode acontecer se o evaluator também retornar `passed`.

## Não objetivos

- execução longa;
- scheduler ou daemon;
- merge, push ou deploy;
- secrets;
- produção.
