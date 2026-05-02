# SPEC Tecnica - No-Diff Prompt Discipline V0

## Componentes

- `app/no_diff_prompt.py`
- `app/codex_handoff.py`
- `app/codex_quiet_runner.py`
- `app/cli.py`

## Regras do contrato

- não imprimir diff;
- não imprimir patch;
- não imprimir conteúdo de arquivo;
- não listar arquivos em excesso;
- não repetir summary;
- salvar evidências em reports;
- manter terminal final abaixo de 20 linhas;
- exigir `changed_files_count`, `report_path` e `validation_status`.

## Integração

- `run-handoff` injeta o contrato no prompt;
- o report de handoff inclui `no_diff_prompt_contract_version`;
- o quiet runner registra `prompt_has_no_diff_contract`;
- o CLI valida o prompt com `no-diff-prompt-check`.

## Validação

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m app.cli no-diff-prompt-contract`
- `python -m app.cli no-diff-prompt-check --prompt-file <PATH>`

