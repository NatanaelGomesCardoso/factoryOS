# PRD - Capsule Execution Policy V0

## Resumo

Criar uma política formal para escolher o executor econômico no FactoryOS.

## Problema

O sistema já confirmou que a cápsula mínima consome muito menos tokens do que o baseline completo do repo, mas ainda faltava uma regra formal para escolher esse caminho de forma consistente.

## Objetivo

- padronizar `capsule` como escolha padrão para tarefas baratas;
- manter `repo_quiet` como fallback quando o repo for necessário;
- reservar `full_repo_review` para segurança e revisão pesada;
- nunca liberar live diretamente.

## Usuários

- mantenedores do FactoryOS;
- automações internas de `factory-start`;
- fluxos de handoff e revisão.

## Requisitos

- comando `capsule-execution-policy`;
- decisão por categoria;
- report com baseline e savings;
- timeout recoverable_with_report;
- validações locais e sem API paga.

## Fora de escopo

- execução live automática;
- alterações em `~/.codex/config.toml`;
- integração com serviços pagos;
- mudanças no harness.
