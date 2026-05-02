# SPEC Tecnica - Worktree Safe Sync V0

## Decisao

Implementar um plano local de sincronização e uma aplicação segura de fast-forward para worktree por run usando Git como fonte de verdade. Não haverá fetch, pull, rebase ou merge com commit automático.

## Status do plano

- `fast_forward_available`
- `already_current`
- `blocked_dirty`
- `blocked_wrong_branch`
- `blocked_not_worktree`
- `blocked_diverged`
- `blocked_missing`

## Arquivos alvo

- `app/run_workspace.py`
- `app/cli.py`
- `app/panel_data.py`
- `app/templates/index.html`
- `reports/worktree-safe-sync-v0-proof.txt`
- `specs/discovery/reuse-first-worktree-safe-sync-v0.md`
- `specs/prd/worktree-safe-sync-v0-prd.md`
- `specs/sprints/014-worktree-safe-sync-v0.json`

## Fluxo do plano

1. validar `run_id`;
2. exigir run existente;
3. localizar o workspace da run com caminho relativo e seguro;
4. consultar `git worktree list` no repo principal;
5. confirmar se o caminho pertence a um worktree real;
6. confirmar o branch esperado `factoryos/run/<run-id>`;
7. verificar se o workspace está limpo;
8. ler `HEAD` do repo principal e do worktree;
9. se `workspace_head == main_head`, retornar `already_current`;
10. se `workspace_head` for ancestral de `main_head`, retornar `fast_forward_available`;
11. se houver sujeira, branch errada, worktree ausente, dados faltando ou divergência real, bloquear.

## Regras de decisao

- `blocked_missing`:
  - run inexistente;
  - workspace inexistente;
  - `main_head` ou `workspace_head` não legível;
  - falha ao verificar ancestralidade por falta de dados.
- `blocked_not_worktree`:
  - workspace existe, mas não é git worktree real.
- `blocked_wrong_branch`:
  - branch atual diferente da esperada.
- `blocked_dirty`:
  - workspace não está limpo.
- `blocked_diverged`:
  - `workspace_head` não é ancestral de `main_head`.
- `already_current`:
  - `workspace_head` igual a `main_head`.
- `fast_forward_available`:
  - worktree real;
  - branch correta;
  - workspace limpo;
  - `workspace_head` ancestral de `main_head`.

## Comandos CLI

`run-workspace-sync-plan <run-id>` deve retornar:

```json
{
  "ok": true,
  "run_id": "....",
  "plan": {
    "status": "fast_forward_available",
    "safe_to_apply": true,
    "main_head": "...",
    "workspace_head": "...",
    "expected_branch": "factoryos/run/....",
    "branch": "factoryos/run/....",
    "reasons": []
  }
}
```

`run-workspace-sync-apply <run-id>` deve:

- rodar o mesmo plano;
- aplicar somente quando `safe_to_apply=true` e `status=fast_forward_available`;
- usar `git -C <worktree_path> merge --ff-only <main_head>` ou equivalente seguro;
- não usar `shell=True`;
- não usar rebase;
- não usar merge com commit;
- após aplicar, rodar readiness de novo;
- retornar JSON com before/after.

## Integracao com readiness e handoff

- após sync bem-sucedido, `run-workspace-readiness` deve voltar `ready`;
- `run-handoff` deve carregar o readiness atualizado;
- `run-execute --dry-run` deve carregar o readiness atualizado;
- `run-execute --live` continua bloqueado sem `FACTORYOS_ENABLE_LIVE_CODEX=1` e ainda depende de readiness `ready`.

## Integracao com painel

- o painel continua read-only;
- o card da última run pode exibir o status do plano de sync;
- não há botão de execução.

## Fora de escopo

- execução live do Codex;
- daemon;
- scheduler;
- App Server;
- MCP;
- integração GitHub/Linear;
- execução paralela;
- deploy;
- fetch, pull, merge com commit ou rebase automático.
