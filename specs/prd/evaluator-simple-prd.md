# PRD — Evaluator simples local

## Objetivo

Criar um evaluator local simples para classificar resultados de validações do FactoryOS.

## Problema

Hoje o usuário e o ChatGPT analisam manualmente se uma etapa passou, falhou ou precisa de correção.

## Solução V1

Criar um módulo Python que recebe sinais simples e retorna uma decisão padronizada em JSON.

## Funcionalidades

- receber sinais de validação;
- classificar resultado;
- retornar JSON;
- expor comando CLI para teste manual;
- não executar Codex;
- não alterar arquivos de projeto.

## Critérios de pronto

- evaluator retorna `passed` quando tudo está ok;
- retorna `stopped_security` quando segurança falha;
- retorna `failed_retryable` quando validação comum falha;
- retorna `needs_chatgpt_review` para risco alto;
- CLI salva resultado com `--out`;
- testes manuais passam.
