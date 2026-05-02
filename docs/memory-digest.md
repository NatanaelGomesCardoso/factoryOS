# Memory Digest

Este documento registra o uso do digest curto de memória do FactoryOS para evitar varrer reports grandes por padrão.

## Objetivo

- manter uma fonte curta para retomada;
- preferir o digest mais recente em vez de abrir centenas de reports;
- carregar reports grandes apenas quando necessário.

## Estrutura

- JSON em `memory/digests/<timestamp>-sprint-<N>.json`
- Markdown em `memory/digests/<timestamp>-sprint-<N>.md`

## Campos principais

- `sprint`
- `commits`
- `decision`
- `summary`
- `key_files`
- `main_reports`
- `risks`
- `next_step`
- `token_summary`

## Regras

- não copiar JSON gigante;
- não copiar segredo;
- manter o digest curto;
- marcar `do_not_expand_by_default=true`.
