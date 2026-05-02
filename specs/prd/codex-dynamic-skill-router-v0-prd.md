# PRD — Codex Dynamic Skill Router V0

## Problema

O handoff pode crescer com reports antigos, stdout/stderr e contexto global desnecessário. Isso aumenta custo, tempo e risco de confusão.

## Objetivo

Criar um roteador local que escolha context pack compacto por categoria de task/run e recomende padrões/skills por nome, sem acionar ou alterar o ambiente global.

## Requisitos

- Categorias: `docs_only`, `code_small`, `code_medium`, `safety_gate`, `live_canary`, `evaluator`, `factory_loop`, `factory_start`, `security_review`.
- Comando `codex-context --task-id`.
- Comando `codex-context --run-id`.
- Incluir arquivos obrigatórios e candidatos seguros.
- Excluir reports antigos desnecessários, stdout/stderr, `workspaces/`, `.venv/`, secrets e arquivos grandes.
- Integrar context pack ao `run-handoff`.

## Não Objetivos

- Não alterar `~/.codex/config.toml`.
- Não remover skills globais.
- Não mexer no harness global.
- Não executar Codex live.
