# Technical Spec - Bounded Long Run Live Canary V0

## Fluxo

1. bloquear qualquer live sem `--cost-aware`;
2. bloquear sem env var, sem `--canary`, sem `--evaluate` ou sem `--run-id`;
3. exigir rehearsal recente válido para a mesma run e mesmos parâmetros;
4. exigir readiness `ready`, sync `already_current`, cost audit `ideal|preferred_ok`, budget/context `ok`;
5. rodar 3 steps sequenciais com `build_factoryos_codex_exec_command`;
6. validar que apenas os arquivos permitidos mudaram;
7. gerar report em `reports/bounded-long-run-live-canary/`;
8. anexar `execution-evaluate`.
