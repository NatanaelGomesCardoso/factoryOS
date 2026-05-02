# Panel Visual System & Navigation V0

## Decisao

O painel adotou um visual de command center local: dark, sobrio, tecnico e denso o suficiente para operacao diaria.

## Sistema visual

- Fundo dark com acentos discretos em verde, ciano, amarelo e vermelho.
- Cards com raio pequeno, borda clara e hierarquia por status.
- Badges padronizados para passed/ready, running, needs_review e blocked/failed.
- Navegacao por anchors para reduzir varredura vertical.
- Layout responsivo em 3, 2 e 1 coluna conforme largura.
- Caminhos longos usam quebra segura para nao gerar overflow horizontal.

## Escopo preservado

- Sem framework JS.
- Sem dependencia externa.
- Sem animacao pesada.
- Sem deploy, push ou API paga.
- Sem segredo em frontend.
- Regras criticas continuam fora do frontend.
