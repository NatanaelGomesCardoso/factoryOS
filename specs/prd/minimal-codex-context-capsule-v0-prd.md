# PRD — Minimal Codex Context Capsule V0

## Problema

Executar tarefas pequenas ou médias no FactoryOS pode carregar contexto demais por herança do repo inteiro.

## Objetivo

Criar uma cápsula Git mínima, previsível e barata para tarefas locais de Codex.

## Requisitos

- criar cápsula em `workspaces/codex-capsules/<timestamp>-<label>/`;
- inicializar Git dentro da cápsula;
- criar `AGENTS.md` mínimo;
- copiar apenas arquivos incluídos;
- copiar digest de memória recente se existir;
- gerar `CAPSULE_MANIFEST.json`;
- manter report em `reports/codex-context-capsules/`;
- expor comandos de create/list/inspect.

## Não objetivos

- alterar config global do Codex;
- executar live automaticamente;
- copiar reports grandes;
- mexer no harness global.

