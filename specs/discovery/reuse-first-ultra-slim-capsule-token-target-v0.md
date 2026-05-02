# Reuse First — Ultra Slim Capsule Token Target V0

## Contexto

Sprints 053.5, 054 e 055 já removeram hooks sample, docs/digest por padrão no canário simples e adicionaram dry-run de aplicação de cápsula.

## Reuso

- Reusar `create_capsule` para montagem e manifest.
- Reusar `cheap-task-factory-e2e` para comparação executável.
- Reusar `codex-capsule-apply --dry-run` para validar export-plan sem aplicar mudanças.

## Decisão

Adicionar apenas `ultra_slim_min` como variação de modo, sem novo executor e sem mudança de política live.
