# SPEC Tecnica - Real Isolated Execution Workspace V0

## Decisão

Implementar isolamento real por run com `git worktree` e branch local `factoryos/run/<run-id>`, sem execução live do Codex nesta sprint.

## Arquivos alvo

- `app/run_workspace.py`
- `app/cli.py`
- `app/codex_handoff.py`
- `app/panel_data.py`
- `app/templates/index.html`
- `app/static/style.css`
- `specs/discovery/reuse-first-real-isolated-execution-workspace-v0.md`
- `specs/prd/real-isolated-execution-workspace-v0-prd.md`
- `specs/sprints/012-real-isolated-execution-workspace-v0.json`
- `reports/real-isolated-execution-workspace-v0-proof.txt`

## Modelo de dados

Adicionar campos opcionais à run:

```json
{
  "workspace_kind": "git_worktree",
  "workspace_branch": "factoryos/run/<run-id>",
  "workspace_state": "prepared"
}
```

## Fluxo de preparação

1. validar `run_id`;
2. carregar a run em `running`;
3. exigir `git status` limpo no repo principal;
4. validar que `workspace_path` é relativo e seguro;
5. criar branch local `factoryos/run/<run-id>`;
6. criar `git worktree` em `workspaces/runs/<run-id>`;
7. atualizar metadata da run com `workspace_kind`, `workspace_branch` e `workspace_state`;
8. não apagar nada automaticamente.

## Status do workspace

`run-workspace-status <run-id>` deve retornar:

- existência do workspace;
- se é `git worktree`;
- branch atual;
- caminho relativo;
- estado de limpeza quando o workspace for um worktree;
- informação de pendência técnica sem escrita.

## Integração com handoff

- `run-handoff` e `run-execute --dry-run` devem ler o estado real do workspace;
- o report deve registrar `workspace_kind`, `workspace_branch` e `workspace_state` quando disponíveis;
- `codex_command` deve apontar para o workspace correto;
- `dry-run` continua sem executar Codex.

## Guardrails

- bloquear path traversal;
- bloquear caminho absoluto vindo de JSON;
- bloquear branch fora do prefixo `factoryos/run/`;
- não usar `shell=True`;
- não remover branch ou worktree automaticamente;
- não sobrescrever diretório populado que não seja o worktree da run;
- manter o painel read-only.

## Fora de escopo

- execução live do Codex;
- daemon;
- scheduler;
- App Server;
- MCP;
- integração GitHub/Linear;
- execução paralela;
- deploy.
