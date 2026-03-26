---
agent: "Python Data Quality Specialist"
description: >
  Audita a qualidade do corpus indexado: chunks abaixo do threshold,
  duplicatas, distribuição de tamanhos e cobertura de documentos.
---

## Contexto

O corpus pode estar em um banco SQLite de trabalho como `data/ebooks_catalog.db` ou no banco padrão configurado do projeto.
O módulo `src/knowledge/corpus_filter.py` define thresholds de qualidade:

- `MIN_CHUNK_CHARS = 60`
- `MIN_ALPHA_RATIO = 0.30`
- `MAX_NUMERIC_RATIO = 0.60`
- `MIN_UNIQUE_WORDS = 5`

## Tarefa

1. Identificar qual banco de trabalho está ativo para indexação e contar:
   - Total de documentos e chunks
   - Chunks com `length(content) < 60`
   - Chunks com menos de 5 palavras únicas
   - Top 10 documentos com mais chunks
   - Distribuição de tamanhos (quartis)
2. Executar `detect_duplicates()` e reportar duplicatas encontradas
3. Verificar se algum documento da pasta `data/entrada/` NÃO está indexado
4. Sugerir ações de limpeza se necessário

## Formato de Saída

```markdown
### Resumo do Corpus
- Docs: XXX | Chunks: XXX
- Chunks abaixo do threshold: XXX (X.X%)
- Duplicatas detectadas: XXX

### Distribuição de Tamanhos
- P25: XXX chars | P50: XXX chars | P75: XXX chars

### Documentos Não Indexados
[lista ou "Nenhum"]

### Ações Recomendadas
1. [ação]
2. [ação]
```
