---
agent: "Python QA Reviewer"
description: >
  Verifica se uma mudança no retriever/scoring causou regressão no baseline de avaliação.
  Executa evaluate, compara com baseline e emite veredicto.
---

## Contexto

O atlas_local usa retrieval híbrido (FTS5 + BM25) com fusão ponderada e RRF.
Qualquer mudança em `src/knowledge/retriever.py`, `src/storage/chunking.py`,
`src/knowledge/corpus_filter.py` ou `src/knowledge/confidence.py` pode causar
regressão silenciosa nos rankings.

## Tarefa

1. Rodar `pytest tests/ -v --tb=short` e verificar que **todos os 181+ testes passam**
2. Rodar o evaluate: `python -m src.main evaluate` e capturar métricas
3. Comparar com o baseline em `data/eval_baseline.json`:
   - MRR >= 0.9643
   - Top-1 >= 0.9286
   - NDCG@5 >= 0.9733
4. Se alguma métrica **caiu mais que 2%**, reportar como REGRESSÃO
5. Se todas as métricas **melhoraram ou mantiveram**, reportar como APROVADO

## Formato de Saída

```markdown
### Resultado: [APROVADO | REGRESSÃO]

| Métrica | Baseline | Atual | Delta |
|---------|----------|-------|-------|
| MRR     | 0.9643   | X.XXXX | +/-X.XX% |
| Top-1   | 0.9286   | X.XXXX | +/-X.XX% |
| NDCG@5  | 0.9733   | X.XXXX | +/-X.XX% |
| P@5     | 0.6714   | X.XXXX | +/-X.XX% |

### Testes: XXX passando, X falhando
### Ação Recomendada: [manter | reverter | investigar]
```
