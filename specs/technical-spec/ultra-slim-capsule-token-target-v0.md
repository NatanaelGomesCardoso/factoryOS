# Technical Spec — Ultra Slim Capsule Token Target V0

## Implementação

`app/codex_context_capsule.py` adiciona `ultra_slim_min` em `CAPSULE_MODES`, usa template Git vazio, escreve `AGENTS.md` mínimo e gera manifest compacto reduzido.

`app/cheap_task_factory_e2e.py` aceita o novo modo, remove includes, desliga digest e monta prompt mínimo para criar apenas `cheap-task-e2e-canary.txt`.

`app/cli.py` expõe o novo valor em `--capsule-mode`.

## Métricas

O report E2E registra:

- `prompt_effective_bytes`
- `agents_bytes`
- `manifest_bytes`
- `capsule_total_bytes`
- `capsule_non_git_bytes`
- `capsule_git_hooks_bytes`
- `tokens_used`
- `target_le_7000`
- `floor_estimate_tokens`
- `accepted_floor_recommendation`

## Segurança

O modo mantém allowlist de escrita e export-plan. O fechamento usa `codex-capsule-apply --dry-run`, sem aplicação real.
