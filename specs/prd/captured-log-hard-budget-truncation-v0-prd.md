# PRD - Captured Log Hard Budget & Truncation V0

## Problema

Mesmo com terminal visível limpo, o stdout/stderr capturado ainda pode ficar enorme e caro para analisar.

## Objetivo

Separar budget visível, budget de aviso, hard limit e truncation preview para o log capturado do quiet runner.

## Não objetivos

- não alterar o harness global;
- não instalar dependências externas;
- não usar API paga;
- não apagar reports antigos;
- não fazer deploy.

## Critérios de pronto

- report inclui sha256 do log completo;
- preview seguro é gerado quando necessário;
- hard limit bloqueia quando ultrapassado;
- compatibilidade com reports antigos permanece;
- saída do terminal continua compacta.

