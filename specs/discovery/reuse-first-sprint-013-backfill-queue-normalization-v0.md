# Reuse First Discovery

## Ideia

Normalizar a pendência antiga da Sprint 013 com backfill conservador, gerando prova explícita e fechando apenas se a evidência local já existir.

## Reaproveitamento obrigatório

- `factory-state-audit` para fotografar a fila antes e depois;
- `factory-state-plan` para confirmar que a Sprint 013 não está bloqueada por risco ativo;
- `task-show`, `task-note` e `task-finish` para inspecionar, anotar e fechar a task;
- `git log --oneline` para comprovar o commit `7c53cd5 feat: add worktree readiness gate v0`;
- specs, proofs e reports já existentes da Sprint 013 e das sprints 014, 018 e 019.

## Critério conservador

Se qualquer peça obrigatória faltar, a decisão permanece `needs_review`.

Não apagar dados, não remover worktree, não executar Codex live, não fazer merge/rebase/fetch/pull.

## Próximo passo

Gerar PRD, SPEC, sprint JSON e um comando de backfill reaproveitável.
