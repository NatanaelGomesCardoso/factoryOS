# Technical Spec - Long Run Expansion Policy V0

## Fluxo

1. validar `run_id`, `target_minutes` e `max_steps`;
2. bloquear path traversal e exigir `target_minutes=30` e `max_steps=6`;
3. localizar o review gate aprovado da Sprint 036;
4. validar `approved_for_expansion_policy=true` e `allowed_to_execute_live=false`;
5. validar cost audit atual em `ideal` ou `preferred_ok`;
6. validar maintenance plan sem deleted_files/removals;
7. validar factory-state-audit e factory-state-plan limpos;
8. gerar report em `reports/long-run-expansion-policies/`.

## Política V0

- `level_0_dry_run_rehearsal`: dry-run já consolidado na Sprint 034;
- `level_1_bounded_live_canary_15m_3steps`: aprovado na Sprint 035;
- `level_2_expanded_bounded_live_30m_6steps`: proposto para uma sprint futura, ainda bloqueado.

## Decisão

- `policy_ready_for_next_sprint` quando todas as condições estiverem satisfeitas;
- `needs_review` para casos conservadores em que a evidência exista mas ainda não seja suficiente;
- `blocked` para falhas claras, inconsistências ou report ausente.
