# First MVP Project Intake

Comando local para criar um intake minimo de MVP a partir de PRD, SPEC e sprints.

## Fluxo

- projeto: `demo-simple-web-mvp`
- kind: `web`
- template: `simple-web-mvp`
- gera discovery, PRD, SPEC e sprint plan rascunho;
- nao instala dependencias;
- nao faz deploy;
- nao faz push;
- mantem live bloqueado.

## Separação

- regras criticas ficam no backend;
- frontend não recebe secrets;
- integração externa só com justificativa explícita.
