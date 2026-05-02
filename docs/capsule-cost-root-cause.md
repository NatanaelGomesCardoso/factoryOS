# Capsule Cost Root Cause V0

Diagnóstico local para explicar custo alto em execuções de cápsula.

O caso-base mostrou prompt pequeno, log pequeno e execução com `cwd` na cápsula, sem vazamento do repo completo. A causa provável ficou no próprio diretório da cápsula: `git init` copiava hooks sample para `.git/hooks`, e o Codex considerava esses arquivos no contexto do `cwd`.

Correção recomendada:

- inicializar cápsulas ultra-slim com template Git vazio;
- não incluir docs nem digest no canário simples;
- manter `AGENTS.md` mínimo;
- registrar `prompt_effective_bytes` e bytes da cápsula;
- manter harness intocado sem prova de causa no harness.

Comando:

```bash
.venv/bin/python -m app.cli capsule-cost-diagnose --e2e-report <PATH>
```
