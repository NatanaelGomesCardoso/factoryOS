# SPEC Tecnica - Evaluator Runner Integration V0

## Decisao tecnica

Reaproveitar o evaluator existente em Python puro e integrar com o task runner local. A V0 nao introduz worker, scheduler, subprocesso, fila distribuida ou automacao de Codex.

## Arquivos provaveis

- `app/task_runner.py`
- `app/cli.py`
- `app/evaluator.py`
- `app/panel_data.py`
- `app/templates/index.html`
- `reports/task-evaluations/`

## Fluxo esperado

1. A CLI recebe `task-evaluate <id>`.
2. O runner valida o id e localiza a task em `tasks/pending/`, `tasks/running/`, `tasks/done/` ou `tasks/failed/`.
3. O runner monta os sinais da avaliacao a partir do JSON local da task e de validacoes simples existentes.
4. A funcao interna do evaluator classifica os sinais.
5. O resultado e persistido como JSON em `reports/task-evaluations/`.
6. O painel carrega o ultimo report de task e exibe o resumo correspondente.

## Formato do report por task

Exemplo minimo:

```json
{
  "task_id": "20260429-171301-sprint-008-evaluator-runner-integration-v0-2cf093",
  "task_title": "Sprint 008 Evaluator Runner Integration V0",
  "task_path": "tasks/running/20260429-171301-sprint-008-evaluator-runner-integration-v0-2cf093.json",
  "report_path": "reports/task-evaluations/20260429-171301-sprint-008-evaluator-runner-integration-v0-2cf093.json",
  "source_status": "running",
  "evaluated_at": "ISO timestamp",
  "evaluator": "app.evaluator.evaluate_signals",
  "decision": "passed|failed_retryable|needs_chatgpt_review|stopped_security",
  "risk": "low|medium|high",
  "reason": "texto curto",
  "next_action": "texto curto",
  "failed_checks": [],
  "inputs": {
    "python_ok": true,
    "json_ok": true,
    "browser_ok": true,
    "security_ok": true,
    "high_risk": false,
    "git_clean": true,
    "git_expected_dirty": false,
    "notes": ""
  }
}
```

## Regras de implementacao

- o report deve ficar sob `reports/task-evaluations/`;
- o nome do arquivo deve ser derivado do id da task;
- o comando nao pode aceitar caminho arbitrario para salvar report;
- o report deve ser salvo com caminho relativo, nunca absoluto;
- o evaluator deve ser chamado diretamente como funcao interna;
- nenhum comando externo pode ser executado;
- nenhuma chamada a Codex pode acontecer;
- a avaliacao nao deve alterar o JSON da task;
- o painel continua sem acoes de mutacao;
- o painel pode mostrar apenas o ultimo report valido.

## Regras de seguranca

- validar `id` com regex restritiva;
- bloquear `..`, caminho absoluto e symlink;
- rejeitar id inexistente com erro explicito;
- impedir escrita fora de `reports/task-evaluations/`;
- nao expor caminho absoluto local;
- nao aceitar input que tente simular ou acionar Codex;
- manter a interface do painel somente leitura.

## Validacoes futuras

- `source .venv/bin/activate` se existir;
- `python -m app.cli task-evaluate <id>`;
- `python -m app.cli task-evaluate <id>` com id inexistente falha;
- `python -m app.cli task-evaluate ../evil` falha;
- `python -m app.cli task-evaluate <TMP_DIR>/evil` falha;
- `python -m app.cli task-evaluate <id>` funciona para tasks em `pending`, `running`, `done` e `failed`;
- `python -m json.tool reports/task-evaluations/<id>.json`;
- `python -m app.cli task-list`;
- `TestClient` com `base_url=http://127.0.0.1` e `GET /` retorna 200;
- `git diff --check`.
