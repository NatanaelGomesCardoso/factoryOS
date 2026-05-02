# Reuse First - Post Expansion Evaluation & Rollback Policy V0

Problema: depois do live expandido, a fábrica precisa decidir se a expansão foi boa o suficiente para continuar e como recuperar com segurança se algo degradar.

O que reutilizar:
- report shape da Sprint 057;
- evaluation/local checks existentes;
- disciplina de reports e indexes;
- padrão de dry-run já usado em outras políticas.

Decisão:
- separar avaliação formal de rollback para não misturar observação com recuperação;
- nunca aplicar rollback automaticamente;
- sempre exigir revisão humana para aplicar qualquer reversão.

Próximo passo:
- implementar evaluation e rollback plan como comandos separados.
