---
agent: "Python Data Quality Specialist"
description: >
  Investiga outliers no corpus do atlas_local: documentos sem chunks úteis,
  repetições excessivas, numeric-heavy docs, tamanhos anômalos e clusters estranhos.
---

## Objetivo

Use este prompt para identificar anomalias estruturais ou estatísticas no corpus.

## Sinais de Entrada

- chunks irrelevantes dominando resultados
- documentos quebrados na indexação
- PDFs com texto ruim
- famílias de documentos quase duplicados
- crescimento estranho do corpus

## Formato de Saída

```markdown
### Outlier Analysis
- Cenário: [indexação | corpus | retrieval support]
- Outliers detectados: [n]
- Clusters detectados: [n]

### Principais Flags
- [flag]: [contagem]

### Exemplos
1. [documento + motivo]
2. [documento + motivo]

### Próxima Ação
[filtrar | revisar loader | ajustar chunking | handoff para retrieval]
```
