# Technical Spec - Expanded Bounded Live Canary V0

## Fluxo

1. bloquear se faltar `--bounded`, `--canary`, `--cost-aware` ou as flags negativas obrigatórias;
2. bloquear se o rehearsal recente da mesma run não estiver válido;
3. bloquear se o review gate de expansão não estiver aprovado;
4. executar no máximo 6 steps e no máximo 30 minutos;
5. registrar `codex_or_capsule_runs`, `token_summary`, heads e arquivos alterados;
6. gerar report e evaluation;
7. marcar `executed_live=true` somente quando tudo passar.

## Segurança

- o workspace continua isolado;
- `master` não pode mudar;
- `changed_files` precisa corresponder à whitelist;
- `token_summary` precisa ficar em limite razoável ou o resultado vira `needs_review`.

## Validação

- `py_compile`;
- `compileall`;
- `git diff --check`;
- `TestClient GET / = 200`.
