# Reversa Legacy Project Intake

## Objetivo

Esta integração adiciona um ponto controlado para usar o Reversa no FactoryOS ao retomar projetos antigos, analisar bases existentes ou preparar um projeto como referência para novos sistemas.

## Escopo V0

- checar disponibilidade local de Node, npm, `reversa` e `npx` sem instalar nada;
- validar que o target está dentro de `<CODE_ROOT>`;
- bloquear `<HARNESS_ROOT>` e `<FACTORYOS_ROOT>` por padrão;
- exigir Git detectado e limpo no target;
- no intake SDD dry-run, aceitar árvore dirty somente quando os paths alterados estiverem restritos a `_reversa_sdd/`, `.reversa/`, `.agents/skills/` ou `AGENTS.md`;
- gerar reports de plano, instalação dry-run, status e intake SDD;
- manter instalação live bloqueada.

## Comandos

```bash
python -m app.cli reversa-global-check
python -m app.cli reversa-project-plan --target <CODE_ROOT>/projeto --dry-run
python -m app.cli reversa-project-install --target <CODE_ROOT>/projeto --dry-run
python -m app.cli reversa-project-status --target <CODE_ROOT>/projeto
python -m app.cli reversa-project-sdd-intake --target <CODE_ROOT>/projeto --dry-run
```

## Segurança

O V0 não executa `reversa install`, não faz push, não faz deploy, não usa API paga e não lê ou move secrets. A integração só registra o que seria criado, lido ou escrito pelo fluxo futuro.

Reports novos ficam em:

- `reports/reversa-project-plans/`
- `reports/reversa-installs/`
- `reports/reversa-project-status/`
- `reports/reversa-sdd-intakes/`

## Próximo Corte

O próximo passo é transformar os artefatos de `_reversa_sdd/` em entrada para intake, PRD e SPEC do FactoryOS, ainda com revisão humana antes de qualquer mutação em projeto real.
