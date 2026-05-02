# Reuse First Discovery

## Ideia

Worktree Safe Sync V0

## Objetivo

Definir a forma mais segura de sincronizar um worktree por run com o `main` local quando e somente quando o fast-forward for comprovadamente seguro.

## Avaliacoes

### Git como fonte de verdade

- usa comandos nativos do Git para `status`, branch, `HEAD`, `worktree list` e ancestralidade;
- evita reimplementar regra crítica fora do Git;
- permite auditar o estado real sem escrita;
- reduz o risco de sync incorreto.

### Fetch ou pull automaticos

- podem alterar o estado sem decisão explícita;
- não são necessários para decidir segurança local;
- fora da proposta desta sprint.

### Merge ou rebase automaticos

- podem reescrever histórico ou criar efeito colateral perigoso;
- não respeitam a política de sync seguro desta fase;
- fora da proposta desta sprint.

## Decisao recomendada

- usar Git como fonte de verdade para `status`, branch, `HEAD` e worktree;
- calcular um plano local de sync antes de qualquer aplicação;
- permitir aplicação somente quando `workspace_head` for ancestral de `main_head`;
- usar apenas fast-forward seguro;
- bloquear quando houver sujeira, branch errada, worktree ausente ou divergência real;
- não fazer fetch, pull, merge com commit ou rebase automático.

## Proximo passo

Gerar PRD, SPEC técnica e sprint JSON da Sprint 014 e implementar o plano/apply seguro localmente.
