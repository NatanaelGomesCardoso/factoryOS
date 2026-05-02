# SPEC Tecnica - Live Codex Canary V0

## Decisao

Implementar um canário live único, síncrono, local e auditável para provar a execução mínima do Codex dentro de um worktree isolado por run.

## Arquivos alvo

- `app/live_canary.py`
- `app/codex_handoff.py`
- `app/cli.py`
- `app/panel_data.py`
- `app/templates/index.html`
- `reports/live-codex-canary-v0-proof.txt`
- `reports/live-canary/<timestamp>-<run-id>.json`
- `specs/discovery/reuse-first-live-codex-canary-v0.md`
- `specs/prd/live-codex-canary-v0-prd.md`
- `specs/sprints/016-live-codex-canary-v0.json`

## Task canary

- usar uma task separada para o canário live;
- risco `high`;
- executor `codex`;
- escopo mínimo e explícito.

## Run canary

- usar uma run separada para a task canary;
- status deve estar `running`;
- workspace deve ser um git worktree real;
- branch deve seguir `factoryos/run/<run-id>`.

## Worktree canary

- preparar o worktree antes da execução live;
- usar Git como fonte de verdade;
- manter o master limpo;
- nunca tocar fora do worktree isolado.

## Comando live

- preferir `codex exec --ignore-user-config --ephemeral --cd <workspace_path> ...`;
- usar `gpt-5.4-mini`;
- reasoning `medium`;
- approval policy `never`;
- sandbox `danger-full-access`;
- prompt fechado e pequeno;
- sem uso de profile global pesado.

## Env var obrigatória

- `FACTORYOS_ENABLE_LIVE_CODEX=1`

Sem essa variável o live falha de forma explícita.

## Timeout e budget

- timeout máximo: `600` segundos;
- 1 execução live;
- sem retry;
- `max_changed_files = 2`;
- path permitido exato: `reports/live-canary/codex-canary.txt`.

## Verificacao pos-execucao

- registrar `master_head_before` e `master_head_after`;
- registrar `workspace_head_before` e `workspace_head_after`;
- verificar `git status --short` no worktree;
- validar lista de arquivos alterados;
- bloquear qualquer alteração fora do path permitido;
- bloquear se o master mudar;
- bloquear se houver push, deploy, segredo ou API paga.

## Report canary

- salvar report em `reports/live-canary/<timestamp>-<run-id>.json`;
- incluir status, `executed_live`, ids, branch, heads, changed files, `codex_exit_code`, paths de stdout/stderr e flags de segurança;
- gerar proof adicional em `reports/live-codex-canary-v0-proof.txt`.

## Fora de escopo

- daemon;
- scheduler;
- App Server;
- MCP;
- GitHub/Linear;
- execução paralela;
- retry loop;
- factory-start;
- merge para master;
- rebase;
- fetch/pull;
- deploy;
- secrets;
- API paga.
