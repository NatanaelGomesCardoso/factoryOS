# Technical Spec - Bounded Live Canary Review Gate V0

## Fluxo

1. validar `run_id` ou `report` com bloqueio de path traversal;
2. localizar o bounded long run live canary mais recente da run ou o report explícito;
3. localizar o execution evaluation relacionado;
4. validar `canary_version=v0`, `executed_live=true`, `steps_completed=3`, `codex_exit_codes` zerados, `changed_files` permitido e `disallowed_files` vazio;
5. validar `master_head_before == master_head_after`, `workspace_head_before == workspace_head_after`, `global_config_dependency=false`, `no_push=true`, `no_deploy=true`, `no_paid_api=true`, `no_secrets=true`;
6. validar `final_decision=passed`, `evaluation_decision=passed`, `target_minutes<=15`, `max_steps<=3`;
7. validar cost audit ideal/preferred_ok, manutenção sem deleted_files/removals e status local de `bwrap`/harness quando disponível;
8. gravar report em `reports/bounded-live-canary-reviews/`.

## Decisão

- `approved_for_expansion_policy` quando todas as evidências passarem;
- `blocked` quando houver violação clara;
- `needs_review` apenas se faltar evidência suficiente para concluir com segurança.
