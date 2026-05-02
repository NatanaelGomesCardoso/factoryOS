# Reuse First Discovery

## Ideia

Task Runner V0 local para FactoryOS

## Criado em

2026-04-29T01:23:04-03:00

## Objetivo desta etapa

Antes de criar arquitetura, PRD, SPEC, Sprint JSON ou prompt para Codex, o ChatGPT deve pesquisar soluções maduras existentes para evitar reinventar a roda.

## Responsabilidade

- ChatGPT: pesquisar, comparar, decidir e gerar a recomendação.
- FactoryOS: registrar o discovery e organizar o fluxo.
- Codex: não deve fazer pesquisa ampla; deve executar somente depois da decisão.

## O que já existe no repo

- `tasks/pending/`
- `tasks/running/`
- `tasks/done/`
- `tasks/failed/`
- painel read-only que já lê essas pastas;
- `app/local_task_router.py` para triagem local;
- `app/panel_data.py` para snapshot do painel.

## Alternativas consideradas

| Opção | Tipo | Licença | Maturidade | Custo | Risco | Decisão |
|---|---|---|---|---|---|---|
| Celery | worker distribuído | OSS | alta | médio | alto para V0 | rejeitar |
| Dramatiq | worker distribuído | OSS | alta | médio | alto para V0 | rejeitar |
| Prefect | orchestration | OSS/comercial | alta | médio/alto | alto para V0 | rejeitar |
| APScheduler | scheduler local | OSS | alta | baixo | adiciona tempo/agenda desnecessários | rejeitar |
| Python puro + JSON + filesystem | custom local | N/A | suficiente para V0 | baixo | baixo | adotar |

## Decisão final

- [ ] usar pronto;
- [ ] adaptar;
- [ ] usar como referência;
- [x] criar pequeno customizado;
- [ ] adiar.

## Justificativa

O V0 precisa apenas controlar ciclo de vida local de tasks em WSL e manter o painel consistente com a fila. Um runner pequeno em Python puro evita infra extra, evita API paga, é auditável por leitura direta dos arquivos e reduz a superfície de falha.

## Impacto no PRD/SPEC

- PRD deve restringir o escopo ao lifecycle local de tasks.
- SPEC deve definir formato de JSON, transições permitidas e bloqueios de path traversal.
- Sprint JSON deve apontar apenas para arquivos locais e validações de filesystem.

## Próximo passo

Gerar PRD, SPEC, Sprint JSON e implementar o runner com comandos locais no CLI.
