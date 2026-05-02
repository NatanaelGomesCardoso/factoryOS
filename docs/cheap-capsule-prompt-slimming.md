# Cheap Capsule Prompt Slimming V0

Modo ultra-slim para canários baratos de cápsula.

O modo `--capsule-mode ultra_slim` cria uma cápsula com `AGENTS.md` compacto, sem docs por padrão, sem digest por padrão e sem hooks sample em `.git/hooks`. O prompt efetivo é curto e medido em `prompt_effective_bytes`.

Comando:

```bash
.venv/bin/python -m app.cli cheap-task-factory-e2e --category docs_only --label final-slim --execute-canary --capsule-mode ultra_slim --max-prompt-bytes 512 --max-capsule-bytes 12000
```

Se os tokens ficarem acima de 7000, o report mantém `ok` quando a execução é segura, mas adiciona warning explícito.
