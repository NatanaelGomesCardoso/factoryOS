# SPEC Tecnica - Worktree Sync & Readiness Gate V0

## Decisao

Implementar um gate local de readiness por run usando Git como fonte de verdade para `status`, branch, HEAD e lista de worktrees. Nao havera merge, rebase, fetch ou pull automaticos.

## Status possiveis

- `ready`
- `blocked`
- `needs_sync_review`

## Arquivos alvo

- `app/run_workspace.py`
- `app/cli.py`
- `app/codex_handoff.py`
- `app/panel_data.py`
- `app/templates/index.html`
- `app/static/style.css`
- `specs/discovery/reuse-first-worktree-readiness-gate-v0.md`
- `specs/prd/worktree-readiness-gate-v0-prd.md`
- `specs/sprints/013-worktree-readiness-gate-v0.json`
- `reports/worktree-readiness-gate-v0-proof.txt`

## Fluxo de readiness

1. validar `run_id`;
2. exigir run existente;
3. localizar o workspace da run com caminho relativo e seguro;
4. consultar `git worktree list` no repo principal;
5. confirmar se o caminho pertence a um worktree real;
6. confirmar o branch esperado `factoryos/run/<run-id>`;
7. verificar se o workspace esta limpo;
8. ler `HEAD` do repo principal e do worktree;
9. se o HEAD divergir, retornar `needs_sync_review`;
10. se qualquer requisito critico falhar, retornar `blocked`;
11. se tudo bater, retornar `ready`.

## Regras de decisao

- `blocked`:
  - run inexistente;
  - path traversal;
  - workspace inexistente;
  - workspace nao e git worktree;
  - branch diferente do esperado;
  - workspace sujo;
  - falha ao ler `HEAD` ou `status`.
- `needs_sync_review`:
  - workspace e worktree real;
  - branch correta;
  - workspace limpo;
  - `HEAD` do worktree difere do `HEAD` principal.
- `ready`:
  - workspace existe;
  - e worktree real;
  - branch correta;
  - workspace limpo;
  - `HEAD` do worktree igual ao `HEAD` principal.

## Comando CLI

`run-workspace-readiness <run-id>` deve retornar:

```json
{
  "ok": true,
  "run_id": "....",
  "workspace": {
    "exists": true,
    "is_worktree": true,
    "branch": "factoryos/run/....",
    "expected_branch": "factoryos/run/....",
    "clean": true,
    "main_head": "...",
    "workspace_head": "...",
    "head_matches_main": true,
    "status": "ready",
    "reasons": []
  }
}
```

## Integracao com handoff

- `run-handoff` deve registrar `readiness_status` e `readiness_reasons` quando disponiveis;
- `run-execute --dry-run` deve carregar o mesmo estado;
- `run-execute --live` deve continuar exigindo `FACTORYOS_ENABLE_LIVE_CODEX=1` e ainda assim bloquear se a readiness nao for `ready`;
- o report nao deve fazer escrita corretiva no workspace.

## Integracao com painel

- o card da ultima run deve mostrar o readiness atual;
- o card do ultimo handoff deve mostrar o readiness registrado;
- o painel continua read-only.

## Fora de escopo

- execucao live do Codex;
- daemon;
- scheduler;
- App Server;
- MCP;
- integracao GitHub/Linear;
- execucao paralela;
- deploy;
- merge ou rebase automatico.
