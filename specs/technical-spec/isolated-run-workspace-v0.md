# SPEC Tecnica - Isolated Run Workspace V0

## Decisão técnica

Criar workspaces isolados por run com diretórios locais e metadata JSON, sem executar Codex automaticamente e sem introduzir daemon, scheduler, App Server ou MCP.

## Arquivos prováveis

- `app/run_workspace.py`
- `app/cli.py`
- `app/panel_data.py`
- `app/templates/index.html`
- `app/static/style.css`
- `specs/discovery/reuse-first-isolated-run-workspace-v0.md`
- `specs/prd/isolated-run-workspace-v0-prd.md`
- `specs/sprints/010-isolated-run-workspace-v0.json`
- `reports/isolated-run-workspace-v0-proof.txt`

## Modelo de dados

### Run

```json
{
  "id": "YYYYMMDD-HHMMSS-task-slug-abc123",
  "task_id": "20260430-000000-example-task-abc123",
  "status": "running",
  "created_at": "2026-04-30T09:00:00-03:00",
  "updated_at": "2026-04-30T09:00:00-03:00",
  "workspace_path": "workspaces/runs/<run-id>",
  "budget": {
    "max_codex_runs": 1,
    "max_retry_attempts": 0,
    "max_changed_files": 20,
    "max_minutes": 60,
    "model": "gpt-5.4-mini",
    "reasoning_effort": "medium",
    "stop_on_security_risk": true
  },
  "notes": []
}
```

## Regras de domínio

- a run depende de uma task existente;
- a run é criada localmente e imediatamente registrada;
- o workspace existe apenas como preparação;
- o JSON é a fonte de verdade;
- o painel mostra apenas leitura;
- o backend valida tudo que importa.

## Ciclo de vida

### `run-create`

- valida `task_id`;
- confirma que a task existe;
- gera `run_id`;
- cria `workspaces/runs/<run-id>/`;
- grava metadata em `runs/running/<run-id>.json`;
- usa budget caps default;
- retorna JSON da run criada.

### `run-list`

- agrupa runs por status;
- retorna contagem e payload sanitizado;
- ignora arquivos invalidos ou fora do formato.

### `run-show`

- valida `run_id`;
- localiza a run em qualquer status;
- retorna o payload persistido com caminho relativo.

### `run-finish`

- aceita apenas runs `running`;
- move a run para `done`;
- atualiza timestamp.

### `run-fail`

- aceita apenas runs `running`;
- exige motivo;
- move a run para `failed`;
- registra o motivo em `notes`.

## Guardrails de segurança

- `run_id` e `task_id` usam validação restrita a slug local;
- path traversal é bloqueado;
- não há escrita fora de `runs/` e `workspaces/runs/`;
- o JSON não expõe caminho absoluto;
- symlinks são rejeitados;
- o painel permanece read-only;
- nenhuma execução automática é adicionada.

## Integração com o painel

- o snapshot do painel carrega a última run válida de `runs/*/*.json`;
- a exibição é somente leitura;
- o painel não cria, move nem executa runs;
- se a última run não for válida, o painel ignora o arquivo.

## Fora de escopo

- chamada automática do Codex;
- execução dentro do workspace;
- daemon;
- scheduler;
- App Server;
- MCP;
- integração GitHub/Linear;
- deploy.

## Validação

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m json.tool specs/sprints/010-isolated-run-workspace-v0.json`
- `python -m app.cli run-list`
- `python -m app.cli run-show <run-id>`
- `python -m app.cli run-finish <run-id>`
- `python -m app.cli run-fail <run-id> --reason "..."`
- `TestClient` com `base_url=http://127.0.0.1` e `GET /` retornando 200
- `git diff --check`
