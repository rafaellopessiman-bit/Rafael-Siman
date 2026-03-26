---
agent: "Python Retrieval Architect"
description: >
  Revisa sinais e features usados no atlas_local, detecta redundância,
  correlação excessiva e risco de score opaco antes de adicionar novas heurísticas.
---

## Objetivo

Use este prompt antes de adicionar ou alterar sinais em retrieval, confidence ou ranking.

## Perguntas Obrigatórias

1. Quais sinais já existem?
2. Quais sinais parecem redundantes?
3. O novo sinal adiciona informação nova ou apenas repete um sinal anterior?
4. A combinação permanece explicável e depurável?
5. Há teste e baseline suficientes para provar ganho real?

## Formato de Saída

```markdown
### Revisão de Feature Selection
- Sinais atuais: [lista]
- Sinais redundantes: [lista]
- Sinal proposto: [nome]
- Decisão: [manter | remover | testar isoladamente]

### Justificativa
[racional técnico]

### Evidência Necessária
1. [teste]
2. [métrica]
3. [trace]
```
