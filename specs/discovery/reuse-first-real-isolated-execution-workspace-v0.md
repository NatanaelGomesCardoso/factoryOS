# Reuse First Discovery

## Ideia

Real Isolated Execution Workspace V0

## Objetivo

Decidir a forma mais segura e madura de isolar o workspace por run antes de qualquer execução live do Codex.

## Avaliações

### `git worktree`

- solução madura e nativa do Git;
- cria isolamento real por branch sem copiar o repo inteiro;
- facilita rastreio, revisão e rollback;
- exige repo limpo e validação cuidadosa antes de criar a nova árvore.

### Cópia de diretório

- simples de implementar;
- maior custo em disco e risco de drift;
- não oferece a mesma semântica de branch/worktree;
- útil apenas como fallback operacional.

### Branch isolada sem `worktree`

- mantém branch local dedicada;
- não entrega isolamento real do filesystem;
- deixa o executor sujeito ao repo principal;
- serve como fallback se `git worktree` falhar no ambiente atual.

## Decisão recomendada

- usar `git worktree` por run quando o repo principal estiver limpo e o comando for seguro;
- manter fallback documentado para branch isolada se o worktree falhar;
- não apagar ou limpar dados automaticamente;
- não iniciar Codex live ainda.

## Próximo passo

Gerar PRD, SPEC técnica e sprint JSON da Sprint 012, depois implementar e validar localmente.
