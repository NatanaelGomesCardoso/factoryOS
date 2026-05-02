# Reuse First — Report Retention & Worktree Lifecycle V0

## Objetivo

Preparar limpeza futura controlada sem apagar nenhum dado agora.

## Reaproveitar

- `app/report_index.py` para entender kinds e pastas;
- `git worktree list` e `runs/` para cruzamento de worktrees;
- `factory-state-audit` e `factory-state-plan` para resumo operacional.

## Decisão V0

Gerar três planos somente leitura:

- retenção de reports;
- lifecycle de worktrees;
- maintenance plan combinando ambos com state hygiene.

## Fora de Escopo

- apagar reports;
- mover reports;
- remover worktrees;
- `git clean`, `git gc` ou `git worktree remove`.
