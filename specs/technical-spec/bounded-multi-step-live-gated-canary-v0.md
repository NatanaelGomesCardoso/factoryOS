# Technical Spec — Bounded Multi-Step Live-Gated Canary V0

## Escopo

Adicionar gate rígido ao `factory-start` live canary para permitir até `2` steps bounded.

## Arquivos

- `app/factory_start.py`
- `app/execution_evaluator.py`
- `app/cli.py`
- `app/panel_data.py`
- `app/templates/index.html`

## Gating

1. exigir `--live --canary --evaluate`;
2. exigir `--run-id` explícito;
3. exigir `FACTORYOS_ENABLE_LIVE_CODEX=1`;
4. exigir `max_steps` entre `1` e `2`;
5. exigir `readiness=ready`;
6. exigir `sync_plan=already_current`;
7. exigir `workspace_kind=git_worktree`.

## Execução

1. criar report final do canário;
2. executar um prompt fechado por step;
3. permitir apenas:
   - `reports/factory-start-live-canary/factory-start-canary-step-1.txt`
   - `reports/factory-start-live-canary/factory-start-canary-step-2.txt`
4. parar no primeiro step com falha;
5. consolidar `changed_files` e `codex_exit_codes`;
6. avaliar com `execution_evaluate`.

## Pós-condições

- `master_head_before == master_head_after`;
- `changed_files` contido nos arquivos permitidos;
- `codex_exit_codes` zerados;
- `no_push`, `no_deploy`, `no_paid_api`, `no_secrets` verdadeiros;
- `final_decision=passed` apenas com evaluator `passed`.
