# Capsule Execution Policy V0

## O que é

Política local que decide quando FactoryOS deve preferir cápsula, repo_quiet, repo_guarded ou full_repo_review.

## Para que serve

- tornar `codex-capsule-run` o caminho econômico padrão para docs e mudanças pequenas;
- evitar abrir o repo completo quando o contexto menor já é suficiente;
- separar tarefas de revisão pesada e segurança do caminho barato;
- manter execução live bloqueada por padrão;
- registrar a decisão com baselines de tokens e justificativa.

## Decisões

- `docs_only` -> `capsule`
- `code_small` -> `capsule`
- `code_medium` -> `capsule` ou `repo_quiet`, conforme `included_files`
- `factory_start` -> `capsule` ou `repo_quiet`, conforme `live_policy`
- `live_canary` -> `repo_guarded`
- `security_review` -> `full_repo_review`
- `heavy_review_only` -> `full_repo_review`

## Comando

- `capsule-execution-policy --task-id <TASK_ID>`
- `capsule-execution-policy --category <CATEGORY>`
- `capsule-execution-policy --run-id <RUN_ID>`

## Regras

- nunca liberar live diretamente;
- timeout só é recoverable quando houver artefatos válidos e validação passar;
- o repo completo precisa de motivo explícito;
- o caminho capsule é a opção padrão para tarefas baratas.
