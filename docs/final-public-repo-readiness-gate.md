# Final Public Repo Readiness Gate V0

Este gate decide se o export limpo esta pronto para revisao humana antes de qualquer GitHub público.

## Comando

```bash
public-repo-readiness-gate --dry-run
```

O comando nunca faz push, nunca cria remoto e nunca publica.

## Checks

O gate verifica:

- `README.md` existe.
- `docs/` existe.
- Help Center esta documentado.
- comandos de release estao documentados.
- `reports/` nao entra no export publico.
- `workspaces/` nao entra no export publico.
- `.env` e secrets nao entram no export publico.
- caminhos locais sensiveis nao entram sem revisao.
- status de licenca esta declarado.
- docs de instalacao/uso existem.
- docs do painel existem.
- docs de seguranca existem.
- docs Reversa existem.
- docs de cleanup/release existem.
- GitHub push nao e autorizado por padrao.

## Decisao

`readiness_decision` pode ser:

- `ready_for_human_review`: pre-requisitos locais atendidos, ainda sem push.
- `needs_review`: algo precisa de revisao humana antes de publicar.
- `failed`: gate bloqueado por erro critico.

Mesmo em `ready_for_human_review`, o resultado continua:

- `safe_to_push=false`
- `safe_to_publish=false`
- `human_review_required=true`
- `no_push=true`
- `no_deploy=true`
- `no_paid_api=true`
- `no_secrets=true`

## Uso esperado

1. Rodar estratégia de release.
2. Rodar plano e validação de export limpo.
3. Rodar este gate.
4. Revisar achados humanos.
5. Só então planejar backup branch e GitHub publish plan.
