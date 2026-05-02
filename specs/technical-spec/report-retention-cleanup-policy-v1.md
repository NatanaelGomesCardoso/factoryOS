# SPEC Técnica - Report Retention & Cleanup Policy V1

## Fluxo

1. varrer `reports/`;
2. classificar por categoria, tamanho e idade;
3. sugerir `keep`, `archive` ou `delete_candidate`;
4. gerar report read-only;
5. nunca apagar automaticamente.

## Segurança

- `safe_to_apply=false`;
- `delete_candidate` sempre exige revisão humana;
- não tocar em Git.
