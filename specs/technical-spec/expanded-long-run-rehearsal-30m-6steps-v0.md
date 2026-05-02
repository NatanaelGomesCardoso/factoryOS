# Technical Spec - Expanded Long Run Rehearsal 30m/6 Steps V0

## CLI

Adicionar:

```bash
expanded-long-run-rehearsal --run-id <RUN_ID> --target-minutes 30 --max-steps 6 --dry-run
```

## Comportamento

1. Validar `run_id` e bloquear path traversal.
2. Exigir `--dry-run`.
3. Exigir `run` em `running`.
4. Localizar policy de expansão aprovada da Sprint 037.
5. Rodar rehearsal controlado de 30m/6 steps em dry-run.
6. Rodar maintenance plan e validar estado/custo/contexto/readiness/sync.
7. Gerar report em `reports/expanded-long-run-rehearsals/`.

## Campos mínimos do report

- `ok`
- `expanded_rehearsal_version`
- `run_id`
- `target_minutes`
- `max_steps`
- `mode`
- `source_expansion_policy_report`
- `long_run_rehearsal_report`
- `maintenance_plan_report`
- `factory_state_audit_report`
- `factory_state_plan_report`
- `allowed_to_execute_live`
- `executed_live`
- `requires_review_gate`
- `requires_new_sprint_for_live`
- `global_config_dependency`
- `token_target_status`
- `budget_status`
- `context_status`
- `final_decision`
- `blockers`
- `warnings`
- `report_path`

## Segurança

- Nenhuma credencial ou segredo pode aparecer em report, log, frontend ou proof.
- O report precisa ser gravado apenas em caminho relativo seguro.
- Path traversal deve ser rejeitado antes de qualquer leitura ou escrita.
