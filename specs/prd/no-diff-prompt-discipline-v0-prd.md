# PRD - No-Diff Prompt Discipline V0

## Problema

O Codex ainda tende a narrar patch, diff e conteúdo de arquivo quando recebe prompts longos ou mal disciplinados.

## Objetivo

Criar um contrato reutilizável de prompt que reduza narrativa de diff sem esconder o resumo final nem as evidências.

## Não objetivos

- não mover regra crítica para frontend;
- não usar API paga;
- não alterar o harness global;
- não remover reports antigos;
- não executar live automaticamente.

## Critérios de pronto

- existe um contrato padrão reutilizável;
- `run-handoff` injeta o contrato;
- o quiet runner detecta o contrato;
- o CLI valida o prompt;
- o terminal final fica curto e previsível.

