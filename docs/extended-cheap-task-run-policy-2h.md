# Extended Cheap Task Run Policy 2h V0

Esta política permite planejar e ensaiar runs leves/baratas de até 2h, tarefa por tarefa, sem liberar execução live.

## Comandos

```bash
./factory-extended-cheap-run-plan --max-minutes 120 --dry-run
./factory-extended-cheap-run-rehearsal --max-minutes 120 --max-tasks 5 --dry-run
./factory-extended-cheap-run-gate --dry-run
```

## Limites

- `max_minutes` padrão: 60.
- `max_minutes` máximo: 120.
- `max_tasks` padrão: 10.
- `max_tasks` máximo: 30.
- Categorias permitidas: `docs_only`, `code_small`, `code_medium`.
- Categorias bloqueadas: `security_review`, `heavy_review`, `live_canary`.

## Gate

`live_execution_allowed=false` e `requires_new_gate_for_live=true` são invariantes da V0. Qualquer run live de 2h precisa de novo gate e autorização explícita.
