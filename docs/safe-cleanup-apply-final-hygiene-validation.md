# Safe Cleanup Apply & Final Hygiene Validation V0

Este fluxo transforma a auditoria profunda em plano conservador de limpeza.

## Comandos

```bash
./factoryos-cleanup-plan --audit-report reports/deep-hygiene-audits/<arquivo>.json --dry-run
./factoryos-cleanup-apply --cleanup-plan reports/deep-hygiene-cleanup-plans/<arquivo>.json --dry-run
./factoryos-cleanup-validate --dry-run
```

## Regras

- Plano é dry-run por padrão.
- Apply V0 só deve ser usado explicitamente e permanece bloqueado quando houver caminho externo.
- Validação usa fixture controlada em `<TMP_DIR>/factoryos-cleanup-fixture`.
- Nada fora do FactoryOS ou da fixture sintética entra em allowlist de aplicação.
- External underscore sempre exige revisão humana.

## Resultado esperado

O fechamento desta sprint prova que `cleanup-apply --dry-run` não apaga arquivos reais e que a validação detecta a fixture sem executar remoção real fora dela.
