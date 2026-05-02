# Segurança do FactoryOS

## Contrato

Toda regra crítica do FactoryOS fica no backend ou nos comandos locais do repo. O painel e qualquer frontend são somente leitura para estado, reports e visualização.

O FactoryOS não deve:

- guardar segredo, token, cookie ou credencial no repo;
- expor segredo em frontend, logs, reports ou vault;
- confiar no cliente para permissão, budget, quota, status de run, transição de task/run ou aprovação de execução live;
- executar deploy, push, pull, fetch, merge ou rebase automático.

## Gate local

Antes de declarar pronto em mudança com automação, execução Codex, reports ou superfície web local, rodar:

```bash
.venv/bin/python -m py_compile app/*.py
.venv/bin/python -m compileall app
.venv/bin/python -m app.cli factory-state-audit
.venv/bin/python -m app.cli factory-state-plan
.venv/bin/python -m app.cli codex-cost-audit
harness security-doctor --source-root <FACTORYOS_ROOT> --strict
git diff --check
```

Para execução Codex, o caminho permitido da fábrica deve passar por `build_factoryos_codex_exec_command` e usar `--ignore-user-config`, `--ephemeral`, `sandbox_mode="workspace-write"` e modelo/reasoning explícitos do `codex_plan`.

## Abuso e automação

- Live Codex exige `FACTORYOS_ENABLE_LIVE_CODEX=1`.
- Canários live precisam de worktree isolado e arquivos permitidos explícitos.
- `context_status != ok` bloqueia live.
- `budget_status != ok` bloqueia qualquer comando Codex gerado pela fábrica.
- Reports não devem conter segredos.

## Publicação e colaboração

CodeQL e Dependabot ficam configurados apenas como segurança de repositório quando houver push futuro; a V1 local não executa deploy/push nem publica nada nesta rodada. A estratégia de fallback local continua sendo `checks/security-boundary.sh` e `harness security-doctor --source-root <FACTORYOS_ROOT> --strict`.

Antes de publicar ou colaborar, criar sprint específica para:

- revisar CodeQL;
- revisar Dependabot;
- revisar secret scanning/push protection;
- reexecutar `harness security-doctor --source-root <FACTORYOS_ROOT> --strict`.
