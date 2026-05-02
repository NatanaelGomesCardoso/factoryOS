# PRD - FactoryOS V1 Readiness Gate V0

## Problema

Antes de entrar nas rodadas GPT-5.5, o FactoryOS precisa de um gate explícito para confirmar se o ciclo funcional atual já está suficientemente maduro.

## Objetivo

Verificar, em dry-run, se os comandos centrais, reports principais, workspace demo, panel, evaluator e contratos de segurança estão funcionando.

## Escopo

- comandos principais;
- reports principais;
- `GET /` do painel;
- `git diff --check`;
- templates disponíveis;
- workspace demo existente;
- evaluator;
- delivery package dry-run;
- retention cleanup dry-run;
- Obsidian sync dry-run;
- quiet runner status contract.

## Fora de escopo

- push;
- deploy;
- API paga;
- secrets;
- qualquer correção automática.

## Resultado esperado

- um `readiness_decision` observável;
- uma lista pequena de falhas ou lacunas;
- nenhuma exceção Python para o caso normal.
