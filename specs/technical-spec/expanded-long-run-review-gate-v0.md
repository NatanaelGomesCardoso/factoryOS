# Technical Spec - Expanded Long Run Review Gate V0

## CLI

Adicionar:

```bash
expanded-long-run-review --run-id <RUN_ID>
expanded-long-run-review --report <REPORT_PATH>
```

## Comportamento

1. Validar `run_id` ou `report`, com path traversal bloqueado.
2. Localizar o rehearsal expandido da Sprint 038.
3. Validar `target_minutes=30`, `max_steps=6` e decisão do rehearsal.
4. Reavaliar maintenance/state atuais.
5. Checar `allowed_to_execute_live=false` e `next_gate_requires_new_sprint=true`.
6. Gerar report em `reports/expanded-long-run-reviews/`.

## Campos mínimos do report

- `ok`
- `expanded_review_gate_version`
- `run_id`
- `source_expanded_rehearsal_report`
- `approved_for_expanded_live_sprint`
- `allowed_to_execute_live`
- `next_gate_requires_new_sprint`
- `recommended_next_sprint`
- `decision`
- `blockers`
- `warnings`
- `report_path`

## Segurança

- Nenhum live novo pode ser liberado pelo review gate.
- Segredos e credenciais continuam proibidos.
- Report e input de report devem usar caminhos relativos seguros.
