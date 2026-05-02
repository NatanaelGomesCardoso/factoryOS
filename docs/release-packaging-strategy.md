# Release Packaging Strategy V0

Esta estrategia prepara o FactoryOS para um release publico limpo sem apagar historico, reports ou evidencias do branch atual.

## Decisao

`release-packaging-strategy --dry-run` deve retornar `strategy_decision=ready` quando existe um plano local suficiente para backup, export limpo, validacao e revisao humana.

Mesmo quando a estrategia estiver pronta:

- `push_allowed=false`
- `safe_to_publish=false`
- `human_review_required=true`
- `no_push=true`
- `no_deploy=true`
- `no_paid_api=true`
- `no_secrets=true`

## Backup recomendado

Antes de qualquer publicacao, criar uma branch e uma tag locais de backup no estado completo atual. O backup preserva historico, reports, workspaces e evidencias para manutencao futura.

Recomendacao gerada pelo comando:

- branch local: `backup/factoryos-pre-public-v1-<data>`
- tag local: `factoryos-pre-public-v1-<data>`

Nenhuma dessas referencias deve ser enviada ao GitHub sem revisao humana.

## Export limpo recomendado

Criar uma copia limpa em `<FACTORYOS_CLEAN_EXPORT>`, sem `.git`, sem reports privados, sem workspaces e sem caches. O export e o candidato para revisao publica, nao o branch operacional completo.

## Entra no release limpo

- `app/`
- `docs/`
- `README.md`
- `requirements.txt` se existir
- specs essenciais e publicaveis
- templates, static e exemplos uteis quando existirem
- `AGENTS.md` somente se estiver adequado para publico

## Fica fora

- `reports/`
- `workspaces/`
- `runs/`
- `logs/`
- `.venv/`
- caches Python e ferramentas
- outputs do Codex
- capsules operacionais
- tarballs de backup
- `.env`, tokens, cookies, chaves e credenciais

## Validacao

Antes de qualquer GitHub remoto:

```bash
release-packaging-strategy --dry-run
clean-public-export-plan --dry-run
clean-public-export-create --dry-run
clean-public-export-validate --dry-run
public-repo-readiness-gate --dry-run
git diff --check
harness security-doctor --source-root <FACTORYOS_ROOT> --strict
```

## Plano GitHub

1. Criar backup local.
2. Gerar export limpo.
3. Validar export localmente.
4. Fazer revisao humana.
5. Criar repo/remoto e push somente com autorizacao explicita.
