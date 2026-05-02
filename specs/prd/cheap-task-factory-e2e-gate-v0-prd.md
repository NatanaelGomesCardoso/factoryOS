# PRD - Cheap Task Factory E2E Gate V0

## Problema

O FactoryOS precisa provar, com baixo custo, que uma task pequena pode seguir o caminho de cápsula ponta a ponta sem aplicar nada no repo real.

## Objetivo

Executar um canário pequeno em cápsula, gerar diff/export-plan e consolidar um report final barato.

## Requisitos

- policy deve decidir `capsule`;
- criar cápsula mínima;
- executar canário curto;
- gerar diff e export-plan;
- normalizar status final;
- manter `executed_live=false`.

