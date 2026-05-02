Você é o executor técnico local do projeto FactoryOS.

Objetivo:
Implementar o Painel Web Local V1 do FactoryOS, conforme PRD, SPEC e Sprint JSON já existentes.

Contexto:
- Repo: <FACTORYOS_ROOT>
- O usuário é leigo; mantenha a solução simples, robusta e fácil de rodar.
- ChatGPT fez a etapa Reuse First e decidiu FastAPI + Jinja2 + CSS simples.
- Codex deve atuar apenas como programador/executor local.
- Não fazer pesquisa ampla na internet.
- Não reinventar arquitetura.
- Não alterar a configuração global do Codex/harness.
- Não executar ChatGPT web.
- Não automatizar troca de contas.
- Não criar login, deploy, banco obrigatório, React/Vite, Streamlit ou NiceGUI.

Arquivos de referência obrigatórios:
- docs/PANEL_DECISION.md
- docs/REUSE_FIRST.md
- specs/prd/panel-v1-prd.md
- specs/technical-spec/panel-v1.md
- specs/sprints/002-panel-v1.json
- AGENTS.md

Escopo permitido:
Pode criar/alterar:
- app/web.py
- app/panel_data.py
- app/templates/base.html
- app/templates/index.html
- app/static/style.css
- requirements.txt, se necessário
- README.md, somente se precisar adicionar instrução curta de execução
- reports/panel-v1-proof.txt, para salvar prova local

Escopo proibido:
Não alterar:
- ~/.codex/*
- <HARNESS_ROOT>/*
- arquivos fora de <FACTORYOS_ROOT>
- segredos, .env, auth.json, tokens, chaves
- Git remote
- deploy
- automações de ChatGPT/Codex

Requisitos funcionais:
1. Criar painel local read-only com FastAPI + Jinja2.
2. Servidor deve rodar em 127.0.0.1:8787.
3. GET /health deve retornar JSON:
   {"ok": true, "service": "factoryos-panel"}
4. GET / deve renderizar HTML.
5. Página deve mostrar:
   - nome FactoryOS;
   - aviso “read-only V1”;
   - últimos commits do Git;
   - arquivos recentes em reports/;
   - arquivos em specs/discovery/;
   - docs úteis em docs/;
   - próximo passo sugerido.
6. O painel não pode executar Codex.
7. O painel não pode alterar arquivos.
8. O painel não pode ler/expor segredos.

Requisitos técnicos:
- Usar pathlib/subprocess com cuidado.
- Não quebrar a CLI existente:
  python3 -m app.cli route ...
  python3 -m app.cli discover ...
- Se criar requirements.txt, incluir apenas dependências mínimas:
  fastapi
  uvicorn
  jinja2
- Se dependências já estiverem disponíveis, não instalar nada global sem necessidade.
- O app deve poder ser iniciado com:
  python3 -m app.web

Validações obrigatórias:
Rode:
- python3 -m py_compile app
- python3 -m app.cli route --out reports/route-panel-implementation-check.json "Atualizar README com instruções. Não alterar código."
- python3 -m json.tool reports/route-panel-implementation-check.json
- iniciar servidor em background local, testar /health com curl, encerrar servidor
- se possível, testar GET / com curl e confirmar que retorna HTML

Sugestão de teste do servidor:
- iniciar com timeout ou background controlado;
- não deixar processo pendurado;
- usar 127.0.0.1:8787;
- salvar evidência em reports/panel-v1-proof.txt.

Critérios de pronto:
- app/web.py existe.
- app/panel_data.py existe.
- templates e CSS existem.
- /health retorna ok.
- / renderiza HTML.
- CLI antiga continua funcionando.
- Validações passam.
- Git diff é pequeno e dentro do escopo.
- Nenhum segredo exposto.
- Nenhum arquivo fora do repo alterado.

Relatório final obrigatório:
1. Resumo do que foi implementado.
2. Arquivos criados/alterados.
3. Dependências adicionadas.
4. Como rodar o painel.
5. Validações executadas e resultados.
6. Riscos/restantes.
7. Próximo passo recomendado.
