# First MVP Capsule Build Canary V0

Comando local para executar um canary pequeno de build dentro de uma cápsula FactoryOS.

## Fluxo

- lê um report de build plan;
- cria uma cápsula mínima com allowlist curta;
- executa o canary somente dentro da cápsula;
- gera diff, export plan e status;
- não altera o repo real.

## Resultado esperado

- `executed_live=false` no repo real;
- `disallowed_files=[]`;
- `no_push`, `no_deploy`, `no_paid_api` e `no_secrets` sempre verdadeiros;
- report local em `reports/mvp-capsule-build-canaries/`.

