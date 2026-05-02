# SPEC Tecnica - Task Runner V0.1

## Decisao tecnica

Manter Python puro, JSON e filesystem local. A V0.1 nao introduz worker, scheduler ou banco.

## Arquivos previstos

- `app/task_runner.py`
- `app/cli.py`
- `app/panel_data.py`
- `app/web.py`
- `app/templates/index.html`
- `app/static/style.css`

## Formato minimo da task

```json
{
  "id": "...",
  "title": "...",
  "description": "...",
  "status": "pending|running|done|failed",
  "risk": "low|medium|high",
  "executor": "manual|local|codex",
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "notes": []
}
```

## Regras de implementacao

- `task-show` procura em `tasks/pending/`, `tasks/running/`, `tasks/done/` e `tasks/failed/`;
- `task-note` adiciona uma nota sem alterar status ou pasta;
- `task-note` valida o JSON antes e depois da escrita;
- o painel usa somente leitura do filesystem;
- a lista do painel continua limitada;
- a visualizacao do JSON usa a rota backend `/view/{area}/{file_path:path}`;
- `tasks/` precisa ser uma area permitida no viewer;
- nenhum comando externo pode ser executado;
- nenhum fluxo pode chamar Codex;
- regras criticas ficam no backend e nao no template.

## Contrato da CLI

- `task-create <title> --description ... --risk ... --executor ...`
- `task-list`
- `task-show <id>`
- `task-note <id> "texto da nota"`
- `task-start <id>`
- `task-finish <id>`
- `task-fail <id>`

## Regras de seguranca

- validar `id` com regex restritiva;
- bloquear `..`, caminho absoluto e symlink;
- rejeitar nota vazia;
- nao expor caminho absoluto local;
- nao abrir secrets;
- nao sobrescrever arquivo sem validacao;
- manter o viewer read-only.

## Plano de abuso

- `task-show ../evil` precisa falhar;
- `task-note ../evil "texto"` precisa falhar;
- `task-show inexistente` precisa falhar;
- `task-note inexistente "texto"` precisa falhar;
- `task-note <id> ""` precisa falhar;
- `GET /view/tasks/../requirements.txt` precisa falhar com 400 ou 404;
- `GET /view/tasks/<status>/arquivo-inexistente.json` precisa falhar com 404;
- arquivo com JSON invalido precisa ser rejeitado no runner.

## Validacao

- `source .venv/bin/activate` se existir;
- `python -m py_compile app/*.py`;
- `python -m compileall app`;
- `python -m json.tool specs/sprints/007-task-runner-v0-1.json`;
- `python -m app.cli task-list`;
- `python -m app.cli task-show 20260429-083531-sprint-007-task-runner-v0-1-usability-6a7c88`;
- `python -m app.cli task-note 20260429-083531-sprint-007-task-runner-v0-1-usability-6a7c88 "Sprint 007 implementada em validação local"`;
- repetir `task-show` e confirmar `notes`;
- `task-show` inexistente deve falhar;
- `task-note` inexistente deve falhar;
- `task-show ../evil` deve falhar;
- `task-note` com nota vazia deve falhar;
- `TestClient` com `base_url=http://127.0.0.1` e `GET /` retorna 200;
- `GET /view/tasks/<running-task>.json` retorna 200;
- `GET /view/tasks/../requirements.txt` retorna 400 ou 404;
- `git diff --check`.
