# Technical Spec - Capsule Apply Dry-Run Contract V0

`codex-capsule-apply` aceita `--dry-run` e `--export-plan`.

O export plan usa `allowed_files` do manifest, compara `changed_files` e preenche `disallowed_files`. O apply report nunca aplica mudanças e só marca `safe_to_apply_later=true` quando todos os arquivos planejados estão permitidos.
