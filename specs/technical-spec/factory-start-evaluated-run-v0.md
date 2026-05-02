# Technical Spec — Factory Start Evaluated Run V0

## Escopo

Adicionar avaliação automática pós-execução ao `factory-start`.

## Arquivos

- `app/factory_start.py`
- `app/execution_evaluator.py`
- `app/report_index.py`
- `app/cli.py`
- `app/panel_data.py`
- `app/templates/index.html`

## Fluxo dry-run avaliado

1. rodar `factory-start` dry-run bounded;
2. persistir o report do start;
3. chamar `evaluate_execution(report_path=<report do start>)`;
4. persistir no report:
   - `evaluation_report`
   - `evaluation_decision`
   - `final_decision`
   - `final_status`
5. para dry-run, o evaluator deve retornar `dry_run_only` ou `needs_review`, nunca `passed` sem evidência live.

## Fluxo live canary avaliado

1. rodar live canary bounded uma vez;
2. persistir o report live;
3. chamar `evaluate_execution(report_path=<report live do factory-start>)`;
4. consolidar `passed` apenas se:
   - `executed_live=true`
   - `codex_exit_code=0`
   - `changed_files` permitido
   - `master` intacto
   - flags `no_push`, `no_deploy`, `no_paid_api`, `no_secrets` verdadeiras
   - evaluator `passed`

## Selector

`execution_evaluator` deve usar `report_index` para evitar source report intermediário ou incorreto.

## Limites

- `max_steps` continua bounded;
- sem retry loop;
- sem paralelismo;
- sem reaproveitar worktree antigo para live nova.
