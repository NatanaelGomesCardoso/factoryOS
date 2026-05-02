# Reuse First Discovery

## Ideia

Captured Log Hard Budget & Truncation V0 para o quiet runner do FactoryOS.

## Criado em

2026-05-01T00:00:00

## Objetivo desta etapa

Antes de ajustar o runner, pesquisar padrões maduros de budgeting, truncation e hash de evidência para evitar guardar log gigante em relatório.

## Responsabilidade

- ChatGPT: pesquisar, comparar e decidir o contrato.
- FactoryOS: registrar o discovery e orientar a implementação.
- Codex: executar somente depois da decisão.

## O que pesquisar

- padrões de truncation seguro de logs;
- checks de tamanho por linhas e bytes;
- hash de evidência;
- preview seguro de logs;
- relatórios compactos para execução automatizada.

## Critérios de avaliação

- maturidade;
- simplicidade;
- compatibilidade local;
- segurança;
- facilidade de auditoria;
- custo de manutenção.

## Decisão final

Adotar uma implementação pequena e local: limites separados para terminal visível, warning budget, hard limit e preview truncado com sha256 do log completo.

