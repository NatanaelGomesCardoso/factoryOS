# GitHub Backup Publish Plan V0

Este plano define como preservar o FactoryOS completo e preparar uma publicacao GitHub limpa sem executar push, deploy, criacao remota ou alteracao de branch/tag durante a Sprint 090.

## Decisao

Os comandos da Sprint 090 sao somente dry-run:

- `github-backup-plan --dry-run`
- `github-publish-plan --dry-run`
- `github-release-checklist --dry-run`

Mesmo quando todos os checks estiverem bons:

- `safe_to_push=false`
- `push_allowed=false`
- `safe_to_execute=false`
- `human_review_required=true`
- `no_push=true`
- `no_deploy=true`
- `no_paid_api=true`
- `no_secrets=true`

## Backup completo sugerido

O backup completo preserva historico, reports e evidencias locais. Ele nao deve ser o repo publico principal.

- branch sugerida: `backup/factoryos-full-history-v1`
- tag sugerida: `factoryos-v1-full-history`
- execucao automatica: proibida nesta sprint
- push da branch/tag: proibido sem autorizacao explicita

Comandos aparecem apenas como preview marcado com `manual_review_required=true`.

## Publicacao GitHub sugerida

Publicar somente o export limpo:

- export limpo: `<FACTORYOS_CLEAN_EXPORT>`
- target: `github-clean-export-v1`
- repo remoto: criado manualmente somente depois de revisao humana

Nao publicar a branch operacional completa com `reports/`, `workspaces/`, `runs/`, logs ou artefatos pesados como repo publico principal.

## Checklist

`github-release-checklist --dry-run` checa:

- Git status limpo;
- reports de release e readiness ok;
- `suspected_secrets_count=0`;
- `local_path_leaks_count=0`;
- docs principais existem;
- `README.md` existe;
- Help Center local responde;
- export readiness esta pronto para revisao humana;
- `safe_to_push=false`;
- `human_review_required=true`.

## Fluxo manual futuro

1. Revisar os reports em `reports/github-publish-plans/`.
2. Validar o export limpo localmente.
3. Revisar conteudo publico por humano.
4. Pedir autorizacao explicita antes de qualquer `git push`.
5. Criar remoto e publicar somente a partir do export limpo, nunca da arvore operacional completa por padrao.
