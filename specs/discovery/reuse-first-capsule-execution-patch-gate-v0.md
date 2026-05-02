# Reuse First — Capsule Execution & Patch Gate V0

## Objetivo

Executar Codex dentro da cápsula e gerar um gate de exportação local sem aplicar mudanças no repo real nesta sprint.

## Reaproveitar

- `app/codex_quiet_runner.py`
- `app/codex_context_capsule.py`
- `app/report_index.py`
- `app/memory_digest.py`

## Decisão V0

O fluxo mede tokens e saída do canário, grava diff da cápsula em arquivo e gera plano de exportação restrito ao manifest.

## Fora de escopo

- aplicação automática no repo real
- deploy
- push/pull/fetch/rebase
- API paga

