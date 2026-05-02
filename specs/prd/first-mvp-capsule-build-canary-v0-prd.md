# PRD - First MVP Capsule Build Canary V0

## Problema

O plano de build já existe, mas ainda falta uma prova pequena e segura de execução em cápsula.

## Objetivo

Executar um canary mínimo de build dentro de uma cápsula controlada e produzir diff/export-plan sem tocar no repo real.

## Escopo

- ler o build plan;
- criar uma cápsula econômica;
- gerar um artefato canário mínimo;
- registrar diff, export-plan e status;
- manter `executed_live=false`.

## Fora de escopo

- aplicar alterações no repo real;
- push;
- deploy;
- dependências externas.

