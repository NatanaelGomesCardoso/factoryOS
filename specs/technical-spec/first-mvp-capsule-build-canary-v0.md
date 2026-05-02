# SPEC Técnica - First MVP Capsule Build Canary V0

## Decisão

Adicionar um comando que carregue um build plan, crie uma cápsula mínima e execute um canary seguro apenas dentro da cápsula.

## Regras

1. aceitar `--dry-run` ou `--execute-canary`;
2. ler um report de build plan existente;
3. em `--execute-canary`, criar cápsula com allowlist mínima;
4. gerar arquivo canário mínimo dentro da cápsula;
5. produzir diff, export-plan e status;
6. nunca aplicar mudanças no repo real.

## Campos principais

- `executed_live=false`;
- `capsule_path`;
- `changed_files`;
- `disallowed_files`;
- `export_plan_report_path`;
- `status_report_path`.

