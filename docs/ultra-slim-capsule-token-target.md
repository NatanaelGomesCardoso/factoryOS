# Ultra Slim Capsule Token Target

Sprint 056 adiciona `--capsule-mode ultra_slim_min` para testar o menor modo seguro de execução write via Codex CLI.

O modo mínimo mantém:

- `AGENTS.md` abaixo de 120 bytes;
- manifest compacto com apenas campos usados por execução/export-plan;
- nenhum docs;
- nenhum digest;
- prompt canário com objetivo e contrato mínimo;
- allowlist restrita a `cheap-task-e2e-canary.txt`.

Resultado local de fechamento: `ultra_slim_min` reduziu bytes de prompt e cápsula, mas a execução write ainda mediu `22930` tokens. A recomendação da sprint é aceitar piso real local acima de `7000` tokens para esse caminho de execução enquanto o Codex CLI/modelo mantiver overhead fixo semelhante.
