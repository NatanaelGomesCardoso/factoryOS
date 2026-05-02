# Reuse First Discovery

## Ideia

Integrar localmente o Task Runner V0 com o evaluator existente para gerar uma avaliação por task, salvar o resultado em JSON e mostrar o ultimo resultado no painel.

## Criado em

2026-04-29T17:13:01-03:00

## Objetivo desta etapa

Antes de ampliar automacao, o FactoryOS precisa fechar o ciclo local entre registrar uma task, avali-la e manter o resultado disponivel no disco e no painel, sem executar Codex automaticamente.

## Responsabilidade

- ChatGPT: definir o corte da sprint, validar o uso de Reuse First e escrever PRD, SPEC e sprint JSON.
- FactoryOS: registrar task, docs e painel local.
- Codex: executar somente a implementacao local futura, sem chamadas externas.

## O que ja existe no repo

- `app/task_runner.py` com create/list/start/finish/fail;
- `app/evaluator.py` com `evaluate_signals`;
- `app/cli.py` com comandos locais;
- `app/panel_data.py` com snapshot do painel;
- `app/templates/index.html` e `app/web.py` com painel read-only e viewer seguro;
- `tasks/pending/`, `tasks/running/`, `tasks/done/` e `tasks/failed/`.

## Alternativas consideradas

| Opcao | Tipo | Licenca | Maturidade | Custo | Risco | Decisao |
|---|---|---|---|---|---|---|
| Celery | worker distribuido | OSS | alta | medio | alto para V0 | rejeitar |
| Prefect | orquestracao | OSS/comercial | alta | medio/alto | alto para V0 | rejeitar |
| APScheduler | scheduler local | OSS | alta | baixo | adiciona agenda desnecessaria | rejeitar |
| worker externo | automacao fora do processo | varia | varia | varia | alto para V0 | rejeitar |
| Python puro + JSON local + evaluator interno | fluxo local | N/A | suficiente | baixo | baixo | adotar |

## Decisao final

- [ ] usar pronto;
- [ ] adaptar;
- [x] usar como referencia;
- [x] criar pequeno customizado;
- [ ] adiar.

## Justificativa

O problema desta sprint e de integracao local, nao de orquestracao. O evaluator atual ja existe e deve ser reaproveitado como funcao interna, porque isso:

- evita nova infraestrutura;
- reduz risco operacional;
- mantem o fluxo auditavel em JSON local;
- permite gerar um report por task sem chamar APIs pagas;
- preserva o painel como leitura do estado local.

## Impacto no PRD/SPEC

- o PRD precisa definir o problema de separacao entre runner e evaluator;
- a SPEC tecnica precisa descrever o comando futuro `task-evaluate <id>`;
- a SPEC precisa definir o report local por task em `reports/task-evaluations/`;
- a sprint JSON precisa cobrir abuso, estados e exibicao do ultimo resultado no painel.

## Proximo passo

Gerar PRD, SPEC tecnica e sprint JSON da Sprint 008 e, depois, implementar a integracao local sem automacao de Codex.
