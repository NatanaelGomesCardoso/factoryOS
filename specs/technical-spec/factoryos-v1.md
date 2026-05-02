# FactoryOS V1 — Technical Spec

## Objetivo

Criar uma fábrica local de MVPs, sites, sistemas, SaaS e automações usando:

- ChatGPT como arquiteto, planejador e revisor.
- Codex como executor técnico controlado.
- Ollama/LLM local como triador barato.
- Playwright/Chromium como sensor visual futuro.
- Git como fonte de estado.
- Harness como camada de validação, segurança e memória.

## Problema

Chamar Codex para qualquer microtarefa custa caro em janela de uso. Probes locais mostraram custo base aproximado de 25k input tokens mesmo para respostas triviais.

## Solução V1

Antes de chamar Codex, o FactoryOS deve rotear cada tarefa:

- `local_only`: resolvida com Python, template ou Ollama.
- `codex_needed`: exige Codex para editar código, rodar testes ou implementar feature.
- `human_review`: exige revisão humana/ChatGPT antes de qualquer execução.

## Escopo V1

Inclui:

1. Roteador local de tarefas.
2. Regras Python determinísticas para riscos críticos.
3. Uso opcional do Ollama.
4. Schemas JSON para tarefa e decisão.
5. Registro de prova em laboratório.
6. Preparação para futura API local.

Não inclui ainda:

1. API FastAPI.
2. Painel web.
3. Playwright.
4. Execução automática do Codex.
5. Deploy.
6. GitHub automation.
7. Troca automática de contas.

## Regras de segurança

Tarefas que envolvem os itens abaixo devem ir para `human_review`:

- autenticação;
- autorização;
- login;
- sessão;
- permissão;
- pagamento;
- dados sensíveis;
- segredo/token/senha;
- banco de dados crítico;
- migração;
- deploy;
- produção;
- segurança crítica.

## Critérios de pronto da V1 inicial

- O roteador local classifica tarefas simples sem chamar Codex.
- Tarefa de bug/código retorna `codex_needed`.
- Tarefa crítica retorna `human_review`.
- JSONs seguem schema.
- Python compila.
- Provas ficam salvas no repo.
- Nenhum segredo é lido ou salvo.

## Reuse First Gate

Antes de implementar funcionalidades grandes, o FactoryOS deve exigir uma decisão Reuse First.

Na V1, essa decisão será feita pelo ChatGPT e registrada no repo. O Codex só deve receber tarefas depois que houver escolha clara entre usar pronto, adaptar, usar como referência, criar pequeno customizado ou adiar.

Esse gate evita reinventar a roda e reduz consumo de tokens do Codex.
