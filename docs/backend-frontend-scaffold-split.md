# Backend/Frontend Scaffold Split V0

O scaffold de workspace passa a criar uma fronteira clara entre backend e
frontend desde o início.

## Objetivo

- criar `backend/` e `frontend/` como áreas distintas;
- manter `docs/` e `reports/` no workspace;
- registrar `PROJECT_STATE.md` e `README.md` no topo;
- bloquear secrets, deploy e APIs pagas.

## Regras

- regras críticas, auth, payment, rate limit, quota e transições de estado ficam no backend;
- frontend cuida de UI, experiência visual e chamadas ao backend;
- nenhum segredo no frontend.

