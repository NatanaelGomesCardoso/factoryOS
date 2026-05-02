# SPEC Técnica - First Project Pilot Runbook V0

## Decisão

Implementar um comando local que descreve a sequência operacional do primeiro projeto piloto sem executar mudanças reais.

## Regras

- dry-run apenas;
- human_review_required=true;
- no_push=true;
- no_deploy=true;
- no_paid_api=true;
- no_secrets=true.

## Fluxo

1. validar o nome do projeto;
1. montar a sequência de etapas;
1. listar os pontos de aprovação humana;
1. registrar os bloqueios permanentes;
1. gravar report local em `reports/project-pilot-runbooks/`.

## Contrato de saída

- `ok=true`;
- `dry_run=true`;
- `runbook` estruturado;
- `steps` enumeradas;
- `report_path` local e seguro.
