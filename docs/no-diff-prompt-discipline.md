# No-Diff Prompt Discipline

## Para que serve

Definir um contrato reutilizável para reduzir narrativa de diff, patch e conteúdo de arquivo em prompts de handoff e execução.

## Regras

- não imprimir diff;
- não imprimir patch;
- não imprimir conteúdo de arquivo;
- não listar arquivos em excesso;
- não repetir summary;
- salvar evidências em reports;
- terminal final máximo de 20 linhas;
- usar `changed_files_count`, `report_path` e `validation_status`.

## Integração

- `no-diff-prompt-contract` imprime o contrato padrão.
- `no-diff-prompt-check --prompt-file <PATH>` verifica se o prompt contém o contrato.
- `run-handoff` injeta o contrato no prompt gerado.
- o quiet runner marca `prompt_has_no_diff_contract` no report.

## Segurança

- o contrato não expõe segredos;
- o contrato não substitui validação real;
- o backend continua sendo a fonte de verdade.
