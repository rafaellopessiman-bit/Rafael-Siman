# Retrospective Sprint Pack - Sprints 1 to 4

## Objetivo

Este documento promove os Sprints 1 a 4 para uma documentacao retrospectiva canonica.

Ele nao afirma que estes sprints tinham artefatos historicos originais com esses nomes no repositorio atual.
Ele registra, de forma organizada, a melhor reconstrucao possivel a partir de evidencia forte no codigo e na documentacao legada.

## Status do Documento

| Campo | Valor |
| --- | --- |
| Tipo | retrospectivo |
| Escopo | Sprints 1, 2, 3 e 4 |
| Base de evidencia | docs legados + codigo Python central |
| Confianca global | alta |

## Padrao Retrospectivo Usado

Cada sprint abaixo segue a mesma estrutura:

1. objetivo retrospectivo
2. escopo normalizado
3. evidencias primarias
4. entregaveis observaveis hoje
5. veredito

## Sprint 1 - Fundacao CLI

### Objetivo retrospectivo

Estabelecer o nucleo funcional do `atlas_local` como ferramenta local de produtividade com quatro comandos principais:

- `index`
- `ask`
- `plan`
- `table`

### Escopo normalizado

- parser CLI
- indexacao local
- retrieval + resposta com LLM
- planejamento estruturado
- consulta tabular segura

### Evidencias primarias

- [STATUS.md](../STATUS.md) registra explicitamente os quatro subcomandos como base funcional
- [main.py](../../src/main.py) concentra os handlers `handle_index`, `handle_ask`, `handle_plan` e `handle_table`
- [EXECUTIVE_SUMMARY.md](../EXECUTIVE_SUMMARY.md) descreve a cobertura de features base do produto

### Entregaveis observaveis hoje

- o comando `index` segue exposto via [main.py](../../src/main.py)
- o comando `ask` segue exposto via [main.py](../../src/main.py)
- o comando `plan` segue exposto via [main.py](../../src/main.py)
- o comando `table` segue exposto via [main.py](../../src/main.py)

### Veredito

O Sprint 1 e bem reconstruido como a fundacao CLI do produto. O numero do sprint nao aparece no historico atual, mas o bloco funcional e coeso e suficientemente delimitado.

## Sprint 2 - Search, cache e indices

### Objetivo retrospectivo

Aumentar a utilidade pratica do sistema base por meio de busca textual eficiente, cache de respostas e persistencia local mais performatica.

### Escopo normalizado

- FTS5 em SQLite
- cache LLM em memoria
- indices do banco local

### Evidencias primarias

- [STATUS.md](../STATUS.md) registra "Phase 1 - Cache & Indices"
- [EXECUTIVE_SUMMARY.md](../EXECUTIVE_SUMMARY.md) registra FTS5 e LLM cache como bloco concluido
- [llm_cache.py](../../src/core/llm_cache.py) implementa `LLMResponseCache`
- [document_store.py](../../src/storage/document_store.py) sustenta a camada de persistencia local

### Entregaveis observaveis hoje

- busca textual com base local ainda faz parte do produto
- cache LLM continua presente em [llm_cache.py](../../src/core/llm_cache.py)
- o repositorio continua tratando FTS5 como acelerador central na base legada

### Veredito

O Sprint 2 e melhor tratado como o sprint de performance inicial do nucleo Python, anterior a qualquer preocupacao agentic.

## Sprint 3 - Paralelismo, async e metricas

### Objetivo retrospectivo

Reduzir latencia operacional e preparar o sistema para workloads maiores sem mudar o modelo de produto.

### Escopo normalizado

- carregamento paralelo de documentos
- cliente async de LLM
- metricas operacionais da camada Python

### Evidencias primarias

- [STATUS.md](../STATUS.md) registra "Phase 2 - Paralelizacao & Async"
- [loader.py](../../src/knowledge/loader.py) usa `ThreadPoolExecutor`
- [llm_client.py](../../src/core/llm_client.py) usa `AsyncGroq`
- [metrics.py](../../src/core/metrics.py) registra metricas e profiling

### Entregaveis observaveis hoje

- carregamento paralelo ainda esta ativo em [loader.py](../../src/knowledge/loader.py)
- caminho async do provider continua em [llm_client.py](../../src/core/llm_client.py)
- metricas Python continuam presentes em [metrics.py](../../src/core/metrics.py)

### Veredito

O Sprint 3 representa a maturacao tecnica do produto original, focada em throughput, nao em novos dominios.

## Sprint 4 - Hardening pre-agentic

### Objetivo retrospectivo

Consolidar a base Python antes da mudanca arquitetural maior introduzida no Sprint 5.

### Escopo normalizado

- cache persistente
- configuracao mais madura
- comportamento mais estavel entre reinicios

### Evidencias primarias

- [STATUS.md](../STATUS.md) registra "Phase C - Cache Persistente & AsyncGroq Real"
- [llm_cache.py](../../src/core/llm_cache.py) implementa `PersistentLLMCache`
- [config.py](../../src/core/config.py) expande os campos de cache persistente
- [EXECUTIVE_SUMMARY.md](../EXECUTIVE_SUMMARY.md) documenta a evolucao do produto ate um estado "producao-pronto"

### Entregaveis observaveis hoje

- `PersistentLLMCache` continua presente em [llm_cache.py](../../src/core/llm_cache.py)
- os campos `LLM_CACHE_PERSISTENT`, `LLM_CACHE_PATH` e `LLM_CACHE_TTL_SECONDS` continuam em [config.py](../../src/core/config.py)

### Veredito

O Sprint 4 fecha a era pre-agentic do `atlas_local`. E a ultima camada retrospectiva antes da trilha historica nomeada do Sprint 5 em diante.

## Veredito do Pack

Os Sprints 1 a 4 agora ficam padronizados como um bloco retrospectivo de fundacao do produto.

Leitura canonica:

- Sprint 1: fundacao CLI
- Sprint 2: search e cache inicial
- Sprint 3: paralelismo, async e metricas
- Sprint 4: hardening pre-agentic
