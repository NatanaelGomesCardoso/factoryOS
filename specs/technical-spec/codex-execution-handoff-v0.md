# SPEC Tecnica - Codex Execution Handoff V0

## Modelo de execução

O FactoryOS não executa Codex automaticamente no caminho padrão. O fluxo da sprint 011 apenas prepara o handoff de uma run existente:

- carregar a run;
- exigir status `running`;
- carregar a task associada;
- gerar prompt local;
- montar comando do Codex;
- salvar report local;
- bloquear live sem variável de ambiente.

## Input

- `run_id`

## Output

Um report JSON em `reports/run-handoffs/<run-id>.json` com:

- `ok`;
- `mode`;
- `run_id`;
- `task_id`;
- `task_title`;
- `task_description`;
- `workspace_path`;
- `workspace_state`;
- `budget`;
- `codex_command`;
- `prompt_path`;
- `report_path`;
- `executed`;
- `live_enabled`;
- `created_at`;
- `technical_pending`.

## Prompt gerado

O prompt deve incluir:

- contexto da task;
- run id;
- workspace path relativo;
- budgets;
- regras de segurança;
- arquivos permitidos;
- validações obrigatórias;
- proibição de segredos;
- proibição de deploy;
- proibição de API paga;
- pedido de relatório final em JSON.

## Comando Codex montado

Forma base esperada para handoff futuro:

```text
codex exec --model <model> --reasoning-effort <reasoning_effort> --cwd <workspace_path> --prompt-file <prompt_path>
```

O comando é registrado como lista de strings. O modo padrão continua dry-run.

## Pasta de reports

- `reports/run-handoffs/`

O prompt e o report devem ficar nessa pasta. O painel só lê o último JSON válido.

## Proteção contra execução acidental

- bloquear `run_id` inválido;
- bloquear path traversal;
- exigir run em `running`;
- usar `subprocess.run(..., shell=False)` para o live;
- não executar live sem `FACTORYOS_ENABLE_LIVE_CODEX=1`;
- não registrar saída sensível do processo em report;
- não mexer no workspace automaticamente se ele estiver vazio;
- registrar a pendência técnica para Sprint 012/013 quando o workspace ainda for apenas um diretório vazio.

## Regra crítica no backend

- a decisão de executar ou não executar é do backend;
- permissões, budgets e validações são resolvidas no backend;
- o painel e o frontend apenas exibem o snapshot;
- nenhum dado sensível deve ser escrito no report;
- nenhum caminho absoluto desnecessário deve ser persistido;
- a execução live continua proibida por padrão.

## Variável de ambiente

- `FACTORYOS_ENABLE_LIVE_CODEX=1`

Sem essa variável, `run-execute --live` deve falhar com erro claro.

## Validações

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m json.tool specs/sprints/011-codex-execution-handoff-v0.json`
- `python -m app.cli task-list`
- `python -m app.cli run-list`
- `python -m app.cli run-handoff <run-id>`
- `python -m app.cli run-execute <run-id> --dry-run`
- `python -m app.cli run-execute <run-id> --live` sem variável deve falhar
- `TestClient` com `base_url=http://127.0.0.1` e `GET /` retornando 200
- `git diff --check`

## Fora de escopo

- execução real e contínua do Codex;
- loop de agentes;
- daemon;
- scheduler;
- App Server;
- MCP;
- GitHub/Linear;
- deploy;
- factory-start;
- worktree real nesta sprint.
