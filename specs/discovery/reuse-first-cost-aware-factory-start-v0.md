# Reuse First — Cost-Aware Factory Start V0

## Objetivo

Transformar o `factory-start` em um gate operacional cost-aware, usando contratos explícitos, planner longo dry-run e maintenance plan antes de qualquer execução futura maior.

## Reaproveitar

- `codex-cost-audits/` como prova de budget alvo;
- `factory-long-run-plan`;
- `factory-maintenance-plan`;
- `codex-plan` e `codex-context`;
- `factory-start` dry-run já existente.

## Decisão V0

Adicionar um caminho `--cost-aware` com dois modos:

- `--plan-only`
- `--dry-run`

Ambos continuam com `allowed_to_execute_live=false` e bloqueio explícito de `--live`.

## Fora de Escopo

- live longo;
- loop de 6h;
- scheduler/daemon;
- deploy, push ou cleanup destrutivo.
