# Capsule Apply Dry-Run Contract V0

Contrato para simular aplicação de mudanças da cápsula no repo real.

Nesta sprint, `codex-capsule-apply` nunca aplica mudanças reais. O comando exige `--dry-run`, lê o manifest e o export plan, valida a allowlist, bloqueia `disallowed_files` e gera um plano de aplicação.

Campos principais:

- `apply_mode=dry_run`;
- `allowed_files`;
- `disallowed_files`;
- `changed_files`;
- `would_apply_files`;
- `safe_to_apply_later`;
- `report_path`.

Comando:

```bash
.venv/bin/python -m app.cli codex-capsule-apply --capsule <PATH> --source-root <PATH> --dry-run --export-plan <PATH>
```
