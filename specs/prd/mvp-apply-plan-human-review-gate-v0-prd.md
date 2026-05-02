# PRD - MVP Apply Plan & Human Review Gate V0

## Problema

Após o canary, ainda não existe um gate explícito para impedir aplicação automática no repo real.

## Objetivo

Criar um plano de aplicação que exponha o que seria aplicado, mas só permita avanço após revisão humana.

## Escopo

- ler o report do canary;
- listar `would_apply_files`;
- bloquear `disallowed_files`;
- marcar `human_review_required=true`;
- manter `safe_to_apply=false`.

## Fora de escopo

- aplicação automática;
- push;
- deploy;
- mudanças sem revisão.

