# Technical Spec — Codex Dynamic Skill Router V0

## Módulo

`app/codex_context_router.py` define categorias, arquivos obrigatórios, candidatos, proibidos, limite de contexto e skills recomendadas por nome.

## Context Pack

O retorno do roteador contém:

- `category`
- `recommended_profile`
- `included_files`
- `excluded_files`
- `context_chars`
- `context_status`
- `reasons`
- `recommended_skills`

## Regras

Incluir preferencialmente `AGENTS.md`, `WORKFLOW.md`, specs relevantes, código diretamente relacionado e report recente por run quando houver.

Excluir `workspaces/`, `.venv/`, stdout/stderr, secrets, arquivos grandes e histórico inteiro de reports.

## Integrações

- `app/cli.py`: `codex-context`.
- `app/codex_handoff.py`: `context_pack`, `context_category`, `included_files`, `context_chars`, `context_status`.

## Segurança

Somente paths relativos seguros. Sem execução de Codex, sem alteração de config global e sem leitura de vault inteiro.
