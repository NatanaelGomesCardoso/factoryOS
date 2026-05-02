# Technical Spec - Capsule Execution Policy V0

## Entrada

- `--task-id`
- `--run-id`
- `--category`

## Saída

JSON compacto com:

- `policy_version`
- `decision`
- `execution_mode_recommendation`
- `capsule_policy_decision`
- `capsule_recommended`
- `reason`
- `expected_token_baseline`
- `expected_token_capsule`
- `expected_savings_percent`
- `requires_export_gate`
- `allowed_to_execute_live`
- `timeout_recovery_policy`
- `recommended_command_kind`

## Regras

- `docs_only` e `code_small` -> `capsule`
- `code_medium` -> `capsule` ou `repo_quiet` conforme `included_files`
- `factory_start` -> `capsule` ou `repo_quiet` conforme `live_policy`
- `live_canary` -> `repo_guarded`
- `security_review` e `heavy_review_only` -> `full_repo_review`
- live nunca é liberado diretamente

## Baseline

- `factoryos_baseline_tokens=23302`
- `capsule_minimal_tokens=1198`
- savings esperado: `94.86%`

## Recuperação de timeout

- classificar como `recoverable_with_report` quando artefatos válidos existirem;
- continuar bloqueando live.
