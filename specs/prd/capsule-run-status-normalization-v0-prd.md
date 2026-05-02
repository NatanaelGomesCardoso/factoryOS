# PRD - Capsule Run Status Normalization V0

## Problema

Hoje a execução de cápsula pode terminar com `captured_log_status=blocked` apenas porque o log capturado contém muitas linhas parecidas com diff, mesmo quando a execução saiu com `exit_code=0` e os gates de exportação passaram.

## Objetivo

Normalizar a decisão final para não classificar esse caso como falha.

## Requisitos

- ler report de execução, export-plan e diff;
- marcar `ok_with_captured_warnings` quando o único bloqueio vier de diff-like lines capturadas;
- manter `blocked` em erros reais;
- expor um CLI compacto.

