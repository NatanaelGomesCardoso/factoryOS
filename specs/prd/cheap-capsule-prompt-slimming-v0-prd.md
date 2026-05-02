# PRD - Cheap Capsule Prompt Slimming V0

Reduzir custo de canários baratos em cápsula sem remover os gates de segurança.

Critérios:

- aceitar `--capsule-mode ultra_slim`;
- aceitar `--max-prompt-bytes` e `--max-capsule-bytes`;
- não incluir docs/digest por padrão no canário simples;
- avisar quando tokens ficarem acima de 7000.
