# Reuse First — Codex Slim Profile Context Budget V0

## Objetivo

Reduzir custo e contexto do Codex no FactoryOS antes de expandir execuções longas.

## Reaproveitar

- Run budget existente em `runs/*/*.json`.
- `app/codex_handoff.py` para prompt/report de handoff.
- `app/factory_start.py` e fluxo de runs existentes, sem alterar execução live.
- `reports/` para prova local e auditoria.

## Decisão V0

Política local no repo, com perfis conceituais e budget estimado por task/run. Não alterar `~/.codex/config.toml` nem configuração global do Codex.

## Fora de Escopo

- Alterar config global do Codex.
- Remover skills globais.
- Mexer no harness global.
- Executar Codex live.
- Deploy, scheduler, daemon, MCP novo ou integrações externas.
