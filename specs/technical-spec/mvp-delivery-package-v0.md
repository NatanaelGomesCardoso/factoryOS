# SPEC Técnica - MVP Delivery Package V0

## Fluxo

1. validar `project` e `workspace`;
2. listar arquivos do workspace;
3. excluir secrets, caches e diretórios gerados;
4. marcar itens incluídos e excluídos;
5. gravar report local em `reports/mvp-delivery-packages/`.

## Segurança

- dry-run only;
- pacote não é criado;
- revisão humana obrigatória.
