# Reuse First Discovery

## Ideia

Task Runner V0.1 local para FactoryOS, com foco em usabilidade operacional.

## Criado em

2026-04-29T08:35:31-03:00

## Objetivo desta etapa

Antes de ampliar automacao, o FactoryOS precisa melhorar a operacao humana sobre tasks locais: visualizar uma task especifica, registrar notas e abrir o JSON com seguranca no painel.

## Responsabilidade

- ChatGPT: revisar o fluxo, decidir escopo e escrever os artefatos de produto e tecnica.
- FactoryOS: registrar tasks, docs e painel local.
- Codex: executar a implementacao local sem chamadas externas.

## O que ja existe no repo

- `tasks/pending/`, `tasks/running/`, `tasks/done/`, `tasks/failed/`;
- `app/task_runner.py` com create/list/start/finish/fail;
- `app/panel_data.py` com snapshot da fila;
- `app/web.py` com file viewer read-only;
- painel web que ja mostra reports, docs e discoveries.

## Alternativas consideradas

| Opcao | Tipo | Licenca | Maturidade | Custo | Risco | Decisao |
|---|---|---|---|---|---|---|
| Celery | worker distribuido | OSS | alta | medio | alto para V0.1 | rejeitar |
| Dramatiq | worker distribuido | OSS | alta | medio | alto para V0.1 | rejeitar |
| Prefect | orquestracao | OSS/comercial | alta | medio/alto | alto para V0.1 | rejeitar |
| APScheduler | scheduler local | OSS | alta | baixo | adiciona agenda desnecessaria | rejeitar |
| Python puro + JSON + filesystem | custom local | N/A | suficiente para V0.1 | baixo | baixo | adotar |

## Decisao final

- [ ] usar pronto;
- [ ] adaptar;
- [x] usar como referencia;
- [x] criar pequeno customizado;
- [ ] adiar.

## Justificativa

O problema agora e de usabilidade, nao de orquestracao. Um runner pequeno em Python puro continua suficiente porque:

- permite `task-show` e `task-note` sem sair do terminal;
- preserva o contrato local em JSON e filesystem;
- evita nova infraestrutura e segue auditavel;
- permite abrir o JSON da task no painel com a mesma rota segura do viewer.

## Impacto no PRD/SPEC

- o PRD precisa explicitar o fluxo de leitura e anotacao de tasks;
- a SPEC tecnica precisa definir a leitura segura de `tasks/` pelo viewer e a validacao de notas;
- o sprint JSON precisa incluir validacao da CLI, do painel e da rota `/view/tasks/...`.

## Proximo passo

Gerar PRD, SPEC e Sprint JSON da V0.1 e implementar as alteracoes locais no runner e no painel.
