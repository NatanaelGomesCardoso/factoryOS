# Reuse First Discovery

## Ideia

Worktree Sync & Readiness Gate V0

## Objetivo

Definir a forma mais madura de impedir execucao live futura quando o workspace por run estiver fora de sincronizacao, sujo ou fora do branch esperado.

## Avaliacoes

### Git como fonte de verdade

- usa comandos nativos do Git para `status`, `branch`, `HEAD` e `worktree list`;
- evita duplicar regra critica em ferramenta propria;
- permite distinguir repo principal, worktree real e diretorio comum;
- suporta auditoria local sem escrita.

### Comparacao propria de arquivos

- exigiria reconstruir semantica que o Git ja fornece;
- aumenta risco de drift e falso positivo;
- nao ajuda a validar branch ou relacao com o repo principal;
- nao e a opcao recomendada.

### Merge ou rebase automatico

- resolve divergencia de forma opaca;
- pode alterar historico sem decisao explicita;
- e perigoso para esta fase;
- fora da proposta desta sprint.

## Decisao recomendada

- usar Git como fonte de status, branch, HEAD e lista de worktrees;
- calcular readiness local antes de qualquer live futura;
- retornar apenas `ready`, `blocked` ou `needs_sync_review`;
- nao fazer merge, rebase, fetch ou pull automaticos;
- manter dry-run seguro e somente observavel.

## Proximo passo

Gerar PRD, spec tecnica e sprint JSON da Sprint 013 e implementar o gate localmente.
