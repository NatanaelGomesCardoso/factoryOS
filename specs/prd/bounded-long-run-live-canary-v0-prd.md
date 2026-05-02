# PRD - Bounded Long Run Live Canary V0

## Objetivo

Executar exatamente um canary live bounded via `factory-start`, com 3 steps máximos, 15 minutos máximos e whitelist rígida de arquivos em worktree isolado.

## Requisitos

1. Só roda com `FACTORYOS_ENABLE_LIVE_CODEX=1`.
2. Só roda com `--live --canary --cost-aware --evaluate --run-id`.
3. Exige rehearsal recente válido para a mesma run.
4. Exige `target_minutes <= 15` e `max_steps <= 3`.
5. Só pode alterar `reports/bounded-long-run-live-canary/step-1.txt`, `step-2.txt` e `step-3.txt`.
