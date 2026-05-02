# Reuse First Discovery

## Ideia

No-Diff Prompt Discipline V0 para o FactoryOS.

## Criado em

2026-05-01T00:00:00

## Objetivo desta etapa

Antes de endurecer o prompt de handoff, pesquisar contratos e padrões que reduzam narrativa de diff/patch sem esconder validação real.

## Responsabilidade

- ChatGPT: pesquisar e decidir o contrato.
- FactoryOS: registrar e distribuir o contrato.
- Codex: seguir o contrato em handoffs e execuções silenciosas.

## O que pesquisar

- contratos de prompt para output compacto;
- práticas de evitar patch narration;
- formatos de resumo final curto;
- campos de report que substituam narrativa longa por métricas.

## Critérios de avaliação

- clareza;
- reuso;
- compatibilidade com o runner atual;
- segurança;
- redução de ruído;
- manutenção local.

## Decisão final

Adotar um contrato pequeno e explícito, com regra de terminal final curto, uso de `changed_files_count`, `report_path` e `validation_status`, e evidência em reports.

