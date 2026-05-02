# PRD — Visualização segura de docs e reports no painel

## Objetivo

Permitir que o usuário visualize arquivos úteis do FactoryOS diretamente no painel local, mantendo o painel read-only.

## Problema

Hoje o painel lista arquivos em reports e docs, mas o usuário ainda precisa abrir terminal, VS Code ou Obsidian para ler o conteúdo.

## Solução V1

Adicionar uma visualização backend segura para arquivos permitidos.
O painel deve mostrar links de visualização em listas de arquivos.
Ao clicar, o usuário abre uma página read-only com metadados e conteúdo textual escapado.

## Escopo V1

- reports;
- docs;
- specs/discovery;
- specs/prd;
- specs/technical-spec;
- specs/sprints.

## Fora do escopo

- editar arquivo;
- deletar arquivo;
- criar arquivo;
- executar arquivo;
- servir diretório inteiro como estático;
- abrir caminho absoluto;
- abrir caminho fora das áreas permitidas;
- renderizar HTML arbitrário como HTML real;
- autenticação;
- banco de dados.

## Requisitos de segurança

- validação deve acontecer no backend;
- frontend não decide permissão;
- bloquear path traversal;
- bloquear symlink;
- bloquear arquivos ocultos;
- bloquear nomes e sufixos sensíveis;
- limitar tamanho máximo lido;
- escapar conteúdo exibido.

## Critérios de pronto

- painel principal continua funcionando;
- rota de visualização abre arquivo permitido;
- path traversal é bloqueado;
- arquivo inexistente é bloqueado;
- HTML dentro de arquivo aparece como texto, não executa;
- validações Python passam;
- TestClient usa base_url http://127.0.0.1;
- Git termina limpo.
