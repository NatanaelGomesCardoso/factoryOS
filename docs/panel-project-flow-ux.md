# Panel Project Flow UX V0

Sprint 085 melhora a leitura do fluxo de projeto/MVP no painel local.

## Decisao

`project_flow_decision=passed`

## Fluxo Exposto

Intake -> PRD -> SPEC -> Build Plan -> Capsule Canary -> Apply Gate -> Workspace -> Evaluator -> Delivery -> Obsidian -> Release.

## Mudancas

- Adicionada ancora `Fluxo` na navegacao do painel.
- Adicionada trilha visual com etapas automaticas locais, gates humanos e release bloqueado.
- Projeto atual ganhou proximo passo operacional.
- O comando `panel-project-flow-check --dry-run` valida o contrato sem executar projeto real.

## Seguranca

O painel permanece read-only. A trilha descreve gates e evidencias, mas nao cria automacao nova nem move regra critica para o frontend.
