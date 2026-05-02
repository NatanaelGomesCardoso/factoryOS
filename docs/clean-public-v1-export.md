# Clean Public V1 Export V0

O export publico limpo cria um candidato revisavel para GitHub sem publicar nada e sem remover evidencias do branch operacional.

## Comandos

```bash
clean-public-export-plan --dry-run
clean-public-export-create --dry-run
clean-public-export-validate --dry-run
```

Por padrao o alvo e `<FACTORYOS_CLEAN_EXPORT>`.

## Comportamento seguro

- `plan` apenas calcula inclusoes, exclusoes e riscos.
- `create --dry-run` simula a copia e nao cria diretorio.
- `create` real so pode usar o caminho informado e bloqueia sobrescrita quando o diretorio ja existe.
- `validate --dry-run` verifica o candidato existente quando houver export real.
- nenhum comando cria remoto, faz push ou publica.

## Entra no export

- `app/`
- `docs/`
- `README.md`
- `requirements.txt`
- `pyproject.toml` se existir
- `LICENSE` se existir
- `templates/`, `static/` e `examples/` quando existirem
- specs essenciais de release publico
- `AGENTS.md` somente como referencia local revisavel

## Fica fora

- `reports/`
- `workspaces/`
- `runs/`
- `logs/`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `*.log`
- `<TMP_DIR>` artifacts
- outputs do Codex
- secrets, `.env`, chaves e credenciais
- tarballs de backup
- capsules operacionais

## Resultado esperado

O JSON retorna:

- `export_decision=ready|needs_review|failed`
- `export_path`
- `included_count`
- `excluded_count`
- `suspected_secrets_count`
- `local_path_leaks_count`
- `safe_to_publish=false`
- `human_review_required=true`

`safe_to_publish` permanece falso ate o gate final e revisao humana.
