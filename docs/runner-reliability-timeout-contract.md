# Runner Reliability & Timeout Result Contract V0

## Para que serve

Registrar o contrato mínimo para que `codex-quiet-run` nunca produza saída inválida quando a execução expirar ou falhar durante a fase de execução.

## Contrato

- `codex-quiet-run --timeout-seconds <N>` controla o timeout da execução quiet.
- O default continua `600`.
- Em timeout, o report precisa ser JSON válido e incluir:
  - `ok=false`
  - `timeout=true`
  - `exit_code=124`
  - `overall_status="timeout"`
  - `error_type="timeout"`
  - `error_message` curto
  - `timeout_seconds`
  - `report_path`
  - `stdout_log_path`
  - `stderr_log_path`
  - `combined_log_path`, quando existir
- `codex-run-result-check --json <PATH>` valida existencia, arquivo nao vazio e JSON valido.
- `codex-run-result-check` retorna `0` para JSON valido, mesmo com `ok=false`.
- `codex-run-result-check` retorna `2` para arquivo ausente, vazio ou JSON invalido.

## Validação

- `python tests/test_codex_quiet_runner_timeout_contract.py`
- `codex-quiet-run --help`
- `codex-run-result-check --help`

