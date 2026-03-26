---
agent: "Python Data Quality Specialist"
description: >
  Audita preparação de dados do atlas_local: limpeza, normalização, padronização,
  outliers, duplicatas e impacto no corpus antes da indexação.
---

## Objetivo

Use este prompt para revisar a qualidade dos dados antes de tuning de retrieval ou mudanças de LLM.

## Checklist

1. Há documentos muito curtos, vazios ou numeric-heavy?
2. Há boilerplate, sumários, índices ou conteúdo repetitivo?
3. Há duplicatas ou famílias quase duplicadas?
4. Há necessidade de normalização, padronização ou imputação?
5. A limpeza deve ocorrer no loader, no chunking ou na indexação?

## Formato de Saída

```markdown
### Auditoria de Data Prep
- Total de documentos: [n]
- Problemas principais: [lista]

### Ações Prioritárias
1. [ação]
2. [ação]
3. [ação]

### Impacto Esperado
- Corpus quality: [efeito]
- Retrieval: [efeito]
- Testes necessários: [lista]
```
