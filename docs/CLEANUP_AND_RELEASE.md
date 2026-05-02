# Limpeza e release

Esta página explica como preparar o FactoryOS para GitHub público sem apagar evidência útil.

## Limpeza interna

Não apague reports antigos nem worktrees manualmente. Primeiro rode auditorias:

```bash
git status --short --branch
.venv/bin/python -m app.cli deep-hygiene-audit --dry-run
.venv/bin/python -m app.cli report-retention-audit --dry-run
.venv/bin/python -m app.cli worktree-lifecycle-plan
```

## Backup branch

Antes de uma estratégia clean, crie uma branch de backup local ou tag local conforme política do mantenedor. Não faça push automático.

## Release clean

Release clean significa publicar código, docs e exemplos necessários, deixando fora caches, secrets, reports privados, workspaces temporários e artefatos grandes.

## O que entra no GitHub público

- `README.md` curto.
- `docs/` publicável.
- `app/` sem secrets.
- `specs/` publicáveis quando não contiverem dado sensível.
- exemplos pequenos e seguros.

## O que fica fora

- `.venv/`;
- caches;
- workspaces de runs;
- reports privados;
- tokens, cookies, chaves e credenciais;
- dumps de banco;
- logs grandes.

## O que revisar antes de push

```bash
.venv/bin/python -m app.cli help-docs-check --dry-run
.venv/bin/python -m app.cli public-export-leak-review --dry-run
git diff --check
harness security-doctor --source-root <FACTORYOS_ROOT> --strict
```

Também revise `.gitignore`, secrets, licença, tamanho de arquivos e se docs mencionam comandos reais. Caminhos locais em material publicável devem aparecer como `<FACTORYOS_ROOT>`, `<PROJECT_ROOT>` ou `<OBSIDIAN_VAULT>`.
