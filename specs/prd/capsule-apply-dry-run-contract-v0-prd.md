# PRD - Capsule Apply Dry-Run Contract V0

Formalizar dry-run de aplicação de cápsula ao repo real.

Critérios:

- bloquear qualquer execução sem `--dry-run`;
- validar allowlist;
- reportar `would_apply_files` e `safe_to_apply_later`;
- não alterar arquivos reais do source.
