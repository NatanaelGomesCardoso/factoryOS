# PRD — Capsule Execution & Patch Gate V0

## Problema

A cápsula reduz contexto, mas o FactoryOS ainda precisa provar que consegue executar Codex nela e controlar a exportação de mudanças.

## Objetivo

Executar Codex dentro da cápsula, registrar custo real e gerar um gate local de diff/export sem aplicar mudanças automaticamente.

## Requisitos

- `codex-capsule-run` usando `codex-quiet-run` com `cwd` na cápsula;
- registrar tokens, output_lines e output_bytes;
- `codex-capsule-diff` salvando diff em arquivo;
- `codex-capsule-export-plan` limitado ao manifest;
- `codex-capsule-apply` somente em dry-run nesta sprint;
- canário pequeno com comparação contra o baseline FactoryOS 23302 tokens.

## Não objetivos

- aplicar mudanças no repo real;
- fazer deploy;
- usar API paga;
- tocar secrets ou config global.

