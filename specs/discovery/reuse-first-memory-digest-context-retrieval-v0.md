# Reuse First Discovery

## Ideia

Sprint 041 Memory Digest & Context Retrieval V0

## Criado em

2026-05-01T00:00:00-03:00

## Objetivo desta etapa

Criar um digest curto de memória e usar esse digest como rota preferencial de contexto antes de abrir reports grandes.

## O que já existe no repo

- `app/codex_context_router.py` para contexto por tarefa e run;
- `reports/` como histórico de prova;
- `app/codex_handoff.py` e `app/factory_start.py` como consumidores de contexto;
- `app/report_index.py` para localizar reports;
- `app/token_usage.py` para resumir custo quando o input permitir.

## Alternativas consideradas

| Opção | Tipo | Custo | Risco | Decisão |
|---|---|---|---|---|
| continuar lendo reports grandes por padrão | caro | alto | alto | rejeitar |
| resumir manualmente em cada retomada | frágil | médio | médio | rejeitar |
| digest curto versionado + router preferindo digest | fonte curta | baixo | baixo | adotar |

## Decisão final

- [x] criar digest curto versionado;
- [x] preferir digest mais recente no router;
- [x] reduzir a necessidade de abrir reports grandes por padrão;
- [ ] copiar report gigante como contexto padrão.

## Próximo passo

Gerar PRD, SPEC técnica, sprint JSON e implementar o roteamento com digest.
