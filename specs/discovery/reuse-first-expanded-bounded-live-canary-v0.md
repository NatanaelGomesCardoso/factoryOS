# Reuse First - Expanded Bounded Live Canary V0

Problema: a fábrica precisa sair do caminho de rehearsals e voltar para um live bounded mais amplo sem abandonar os controles econômicos e seguros já criados.

O que reutilizar:
- rehearsal 30m/6 steps da Sprint 038;
- review gate da Sprint 039;
- budget, memory digest, quiet runner, compact harness e capsule policy das Sprints 040-056;
- report indexing e avaliação existentes.

Decisão:
- criar um novo comando bounded expandido em vez de inflar o fluxo legado;
- manter o live dentro de worktree isolado;
- registrar tokens, heads e lista de arquivos em report.

Próximo passo:
- implementar o canário expandido e só então avaliar se a expansão virou caminho principal.
