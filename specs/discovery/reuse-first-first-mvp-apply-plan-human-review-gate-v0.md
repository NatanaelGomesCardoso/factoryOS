# Reuse First Discovery - MVP Apply Plan & Human Review Gate V0

## Ideia

Transformar o resultado do canary em um plano de aplicação que nunca aplica automaticamente.

## O que reutilizar

- report do canary;
- export plan;
- lista de `would_apply_files`;
- flags de segurança e gate humano.

## Decisão esperada

- revisão humana obrigatória;
- `safe_to_apply=false` por padrão;
- nenhum efeito colateral no repo real.

