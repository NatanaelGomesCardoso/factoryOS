# Reuse First Discovery - First Project Pilot Runbook V0

## Ideia

Criar um runbook prático para o primeiro projeto piloto do FactoryOS.

## Objetivo

Encontrar o menor fluxo operacional seguro para sair da entrada do projeto até a retenção dos reports, sem acionar push, deploy, APIs pagas ou secrets.

## O que reutilizar

- fluxo de intake já existente;
- PRD e SPEC curtos;
- sprint plan mínimo;
- build plan e capsule canary já aprovados;
- apply gate humano;
- workspace scaffold com backend e frontend separados;
- evaluator MVP;
- delivery package dry-run;
- Obsidian sync;
- report retention cleanup plan.

## Decisão esperada

- usar um runbook sequencial e explícito;
- manter pontos de aprovação humana em cada corte crítico;
- não automatizar ações irreversíveis.
