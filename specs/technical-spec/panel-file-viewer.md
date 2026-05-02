# SPEC Técnica — Visualização segura de arquivos no painel

## Decisão técnica

Implementar um viewer read-only no backend FastAPI atual.
Não servir reports/docs como diretórios estáticos.
O backend deve validar o caminho antes de ler qualquer arquivo.

## Arquivos previstos

- app/web.py;
- app/panel_data.py;
- app/templates/index.html;
- app/templates/file_view.html;
- app/static/style.css;
- reports/panel-file-viewer-proof.txt.

## Rota proposta

GET /view/{area}/{file_path:path}

## Áreas permitidas

- reports -> reports;
- docs -> docs;
- discovery -> specs/discovery;
- prd -> specs/prd;
- technical-spec -> specs/technical-spec;
- sprints -> specs/sprints.

## Validação de caminho

O backend deve:

- rejeitar área desconhecida;
- rejeitar caminho vazio;
- rejeitar caminho absoluto;
- rejeitar ..;
- resolver o caminho final;
- garantir que o caminho final continua dentro do diretório permitido;
- rejeitar symlink;
- rejeitar diretório;
- rejeitar arquivo oculto;
- rejeitar nomes/sufixos sensíveis;
- limitar tamanho máximo lido.

## Renderização

- JSON deve ser exibido com pretty print como texto;
- Markdown deve ser exibido como texto escapado;
- HTML deve ser exibido como texto escapado;
- Arquivo não textual deve mostrar mensagem segura;
- Arquivo grande demais deve mostrar mensagem segura.

## Validações obrigatórias

- python -m py_compile app/*.py;
- python -m compileall app;
- TestClient com base_url http://127.0.0.1;
- abrir arquivo permitido em reports;
- abrir arquivo permitido em docs ou specs;
- bloquear path traversal;
- bloquear arquivo inexistente;
- confirmar que HTML não é executado como HTML;
- git diff --check.
