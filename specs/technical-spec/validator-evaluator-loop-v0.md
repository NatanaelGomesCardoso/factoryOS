# SPEC Técnica - Validator/Evaluator Loop V0

## Decisão técnica

Implementar o evaluator em Python puro, no mesmo estilo dos comandos locais já existentes, reaproveitando reports e validações já disponíveis.

## Arquivos prováveis

- `app/execution_evaluator.py`
- `app/cli.py`
- `app/panel_data.py`
- `app/templates/index.html`
- `reports/execution-evaluations/`

## Entrada

- `run_id`
- ou `report_path` relativo dentro de `reports/`

## Saída

Evaluation report JSON com:

- `ok`;
- `run_id`;
- `source_report`;
- `decision`;
- `checks`;
- `reasons`;
- `created_at`.

## Verificações

- report existe;
- JSON válido;
- `executed_live` quando aplicável;
- `codex_exit_code`;
- `changed_files`;
- `allowed_files_changed`;
- `master_head_before == master_head_after` quando aplicável;
- `no_push`;
- `no_deploy`;
- `no_paid_api`;
- `no_secrets`;
- `readiness_status`;
- `sync_plan_status`;
- validações Python;
- painel `GET /`.

## Regras de implementação

- aceitar apenas report path relativo dentro de `reports/`;
- bloquear `..`, caminho absoluto e symlink;
- não usar `shell=True`;
- não executar Codex live;
- não fazer deploy;
- não usar API paga;
- não ler secrets;
- não fazer merge ou push;
- manter o painel read-only.

## Fora de escopo

- daemon;
- scheduler;
- retry automático;
- execução paralela;
- App Server;
- MCP;
- integração GitHub/Linear;
- factory-start;
- merge automático;
- deploy automático.
