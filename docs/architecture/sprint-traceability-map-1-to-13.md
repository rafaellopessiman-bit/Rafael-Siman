# Sprint Traceability Map - 1 to 13

## Objetivo

Este arquivo padroniza a rastreabilidade dos sprints do `atlas_local` no estado atual do repositorio.

Ele existe para responder, de forma objetiva:

- quais sprints possuem evidencia explicita no repo
- quais sprints so podem ser reconstruidos como inferencia forte
- quais arquivos sustentam cada conclusao

## Taxonomia de Evidencia

Use sempre uma destas classificacoes:

| Classificacao | Significado |
| --- | --- |
| `explicit` | O numero do sprint aparece nominalmente em docs, testes ou comentarios estruturais do codigo |
| `retrospective` | O sprint foi documentado depois, com base forte em evidencia local, mas nao possui trilha historica original limpa no repo atual |
| `not-found` | Nao ha evidencia suficiente para mapear com seguranca |

## Conclusao Canonica

- O repositorio atual contem evidencia de evolucao ate o **Sprint 13**.
- A trilha **explicita** vai de **Sprint 5 a Sprint 8** e de **Sprint 10 a Sprint 13**.
- Os **Sprints 1 a 4** agora possuem documentacao **retrospectiva canonica** em [retrospective-sprints-1-to-4-foundation.md](./retrospective-sprints-1-to-4-foundation.md).
- O **Sprint 9** agora possui documentacao **retrospectiva canonica** em [retrospective-sprint-9-security-hardening.md](./retrospective-sprint-9-security-hardening.md).

## Mapa Resumido

| Sprint | Classificacao | Confianca | Escopo normalizado | Evidencia primaria |
| --- | --- | --- | --- | --- |
| 1 | `retrospective` | alta | Fundacao CLI: `index`, `ask`, `plan`, `table` | [retrospective-sprints-1-to-4-foundation.md](./retrospective-sprints-1-to-4-foundation.md), [main.py](../../src/main.py) |
| 2 | `retrospective` | alta | Search/cache basico: FTS5, cache LLM, indices | [retrospective-sprints-1-to-4-foundation.md](./retrospective-sprints-1-to-4-foundation.md), [llm_cache.py](../../src/core/llm_cache.py), [document_store.py](../../src/storage/document_store.py) |
| 3 | `retrospective` | alta | Paralelismo, async e metricas | [retrospective-sprints-1-to-4-foundation.md](./retrospective-sprints-1-to-4-foundation.md), [loader.py](../../src/knowledge/loader.py), [llm_client.py](../../src/core/llm_client.py), [metrics.py](../../src/core/metrics.py) |
| 4 | `retrospective` | media-alta | Hardening pre-agentic: cache persistente e config madura | [retrospective-sprints-1-to-4-foundation.md](./retrospective-sprints-1-to-4-foundation.md), [llm_cache.py](../../src/core/llm_cache.py), [config.py](../../src/core/config.py) |
| 5 | `explicit` | muito alta | Multi-agent runtime foundation | [backlog-sprint-5-to-8.md](./backlog-sprint-5-to-8.md), [SPRINT5_REFLECTION.md](../SPRINT5_REFLECTION.md), [app.e2e-spec.ts](../../test/app.e2e-spec.ts) |
| 6 | `explicit` | muito alta | Quality and evaluation system | [backlog-sprint-5-to-8.md](./backlog-sprint-5-to-8.md), [evaluation.module.ts](../../src/domains/evaluation/evaluation.module.ts), [evaluation.e2e-spec.ts](../../test/evaluation.e2e-spec.ts) |
| 7 | `explicit` | muito alta | Control plane and operations | [backlog-sprint-5-to-8.md](./backlog-sprint-5-to-8.md), [control.module.ts](../../src/domains/control/control.module.ts), [control.e2e-spec.ts](../../test/control.e2e-spec.ts) |
| 8 | `explicit` | muito alta | Product surfaces and hardening | [backlog-sprint-5-to-8.md](./backlog-sprint-5-to-8.md), [smoke-ask.e2e-spec.ts](../../test/smoke-ask.e2e-spec.ts), [smoke-extract.e2e-spec.ts](../../test/smoke-extract.e2e-spec.ts), [smoke-act.e2e-spec.ts](../../test/smoke-act.e2e-spec.ts) |
| 9 | `retrospective` | alta | Seguranca de acesso: API key guard e rotas publicas | [retrospective-sprint-9-security-hardening.md](./retrospective-sprint-9-security-hardening.md), [smoke-auth.e2e-spec.ts](../../test/smoke-auth.e2e-spec.ts) |
| 10 | `explicit` | muito alta | Production hardening: health detailed, correlation ID, async indexing, throttlers | [smoke-s10.e2e-spec.ts](../../test/smoke-s10.e2e-spec.ts), [app.module.ts](../../src/app.module.ts) |
| 11 | `explicit` | muito alta | Persistent queue plus observability | [smoke-s11.e2e-spec.ts](../../test/smoke-s11.e2e-spec.ts), [app.module.ts](../../src/app.module.ts) |
| 12 | `explicit` | muito alta | Metrics endpoint, cache, pagination, upload, scheduler | [smoke-s12-full.e2e-spec.ts](../../test/smoke-s12-full.e2e-spec.ts), [smoke-s12-metrics.e2e-spec.ts](../../test/smoke-s12-metrics.e2e-spec.ts) |
| 13 | `explicit` | muito alta | Hardening final: paginacao, error envelopes, health configuravel | [smoke-s13-hardening.e2e-spec.ts](../../test/smoke-s13-hardening.e2e-spec.ts) |

## Detalhamento por Sprint

### Sprint 1 - Fundacao CLI

- Classificacao: `retrospective`
- Escopo normalizado:
  - comandos principais `index`, `ask`, `plan`, `table`
  - base local em Python com SQLite
- Evidencias:
  - [STATUS.md](../STATUS.md) descreve os 4 subcomandos como base funcional
  - [main.py](../../src/main.py) concentra os handlers `handle_index`, `handle_ask`, `handle_plan` e `handle_table`
- Nota:
  - o numero "Sprint 1" nao aparece, mas este e o nucleo funcional mais antigo e coeso do produto

### Sprint 2 - Search e cache basico

- Classificacao: `retrospective`
- Escopo normalizado:
  - FTS5
  - cache LLM
  - indices do banco
- Evidencias:
  - [STATUS.md](../STATUS.md) registra "Phase 1 - Cache & Indices"
  - [llm_cache.py](../../src/core/llm_cache.py) implementa o cache LLM
  - [document_store.py](../../src/storage/document_store.py) sustenta FTS5 e persistencia local
- Nota:
  - este bloco e forte o bastante para ser tratado como um sprint legado autonomo

### Sprint 3 - Paralelismo, async e metricas

- Classificacao: `retrospective`
- Escopo normalizado:
  - carregamento paralelo
  - cliente LLM async
  - metricas basicas
- Evidencias:
  - [STATUS.md](../STATUS.md) registra "Phase 2 - Paralelizacao & Async"
  - [loader.py](../../src/knowledge/loader.py) usa `ThreadPoolExecutor`
  - [llm_client.py](../../src/core/llm_client.py) usa `AsyncGroq`
  - [metrics.py](../../src/core/metrics.py) centraliza metricas da camada Python

### Sprint 4 - Hardening pre-agentic

- Classificacao: `retrospective`
- Escopo normalizado:
  - cache persistente
  - configuracao mais madura
  - base pronta para a guinada agentic
- Evidencias:
  - [STATUS.md](../STATUS.md) registra "Phase C - Cache Persistente & AsyncGroq Real"
  - [llm_cache.py](../../src/core/llm_cache.py) implementa `PersistentLLMCache`
  - [config.py](../../src/core/config.py) consolida os campos de configuracao de cache
- Nota:
  - esta e a ultima camada grande antes do plano explicito de Sprint 5 a 8

### Sprint 5 - Multi-agent runtime foundation

- Classificacao: `explicit`
- Escopo normalizado:
  - registry de agentes
  - handoffs
  - memoria de conversa
  - orchestrator
- Evidencias:
  - [backlog-sprint-5-to-8.md](./backlog-sprint-5-to-8.md)
  - [sprint-5-to-8-blueprint.md](./sprint-5-to-8-blueprint.md)
  - [SPRINT5_REFLECTION.md](../SPRINT5_REFLECTION.md)
  - [app.e2e-spec.ts](../../test/app.e2e-spec.ts)

### Sprint 6 - Quality and evaluation system

- Classificacao: `explicit`
- Escopo normalizado:
  - evaluation domain
  - critic agent
  - datasets e eval runs
- Evidencias:
  - [backlog-sprint-5-to-8.md](./backlog-sprint-5-to-8.md)
  - [evaluation.module.ts](../../src/domains/evaluation/evaluation.module.ts)
  - [evaluation.e2e-spec.ts](../../test/evaluation.e2e-spec.ts)

### Sprint 7 - Control plane and operations

- Classificacao: `explicit`
- Escopo normalizado:
  - control plane
  - control tower
  - alertas e audit trail operacional
- Evidencias:
  - [backlog-sprint-5-to-8.md](./backlog-sprint-5-to-8.md)
  - [control.module.ts](../../src/domains/control/control.module.ts)
  - [control.e2e-spec.ts](../../test/control.e2e-spec.ts)

### Sprint 8 - Product surfaces and hardening

- Classificacao: `explicit`
- Escopo normalizado:
  - surfaces Ask, Extract e Act
  - runbooks operacionais
  - smoke suites dedicadas
- Evidencias:
  - [backlog-sprint-5-to-8.md](./backlog-sprint-5-to-8.md)
  - [smoke-ask.e2e-spec.ts](../../test/smoke-ask.e2e-spec.ts)
  - [smoke-extract.e2e-spec.ts](../../test/smoke-extract.e2e-spec.ts)
  - [smoke-act.e2e-spec.ts](../../test/smoke-act.e2e-spec.ts)
  - [agent-runtime-runbook.md](../operations/agent-runtime-runbook.md)

### Sprint 9 - Seguranca de acesso

- Classificacao: `retrospective`
- Escopo normalizado:
  - API key guard
  - rotas publicas explicitamente marcadas
  - smoke de autenticacao
- Evidencias:
  - [api-key.guard.ts](../../src/shared/guards/api-key.guard.ts)
  - [public.decorator.ts](../../src/shared/guards/public.decorator.ts)
  - [smoke-auth.e2e-spec.ts](../../test/smoke-auth.e2e-spec.ts)
- Nota:
  - o sprint agora possui documentacao retrospectiva canonica, preservando a honestidade de que a trilha historica original nao estava nomeada de forma limpa

### Sprint 10 - Production hardening

- Classificacao: `explicit`
- Escopo normalizado:
  - `GET /health/detailed`
  - correlation ID
  - `POST /knowledge/async`
  - named throttlers
- Evidencias:
  - [smoke-s10.e2e-spec.ts](../../test/smoke-s10.e2e-spec.ts)
  - [app.module.ts](../../src/app.module.ts)

### Sprint 11 - Persistent queue plus observability

- Classificacao: `explicit`
- Escopo normalizado:
  - driver async selecionavel
  - fila persistente
  - correlacao preservada em jobs
  - defaults de observabilidade
- Evidencias:
  - [smoke-s11.e2e-spec.ts](../../test/smoke-s11.e2e-spec.ts)
  - [app.module.ts](../../src/app.module.ts)

### Sprint 12 - Metrics, cache, pagination, upload, scheduler

- Classificacao: `explicit`
- Escopo normalizado:
  - endpoint `/metrics`
  - paginacao em `knowledge`
  - upload de documentos
  - integracao de cache
  - scheduler carregado
- Evidencias:
  - [smoke-s12-full.e2e-spec.ts](../../test/smoke-s12-full.e2e-spec.ts)
  - [smoke-s12-metrics.e2e-spec.ts](../../test/smoke-s12-metrics.e2e-spec.ts)

### Sprint 13 - Hardening final de envelopes e paginacao

- Classificacao: `explicit`
- Escopo normalizado:
  - paginacao em conversas, runs e eval runs
  - respostas de erro enriquecidas
  - health detalhado configuravel
- Evidencias:
  - [smoke-s13-hardening.e2e-spec.ts](../../test/smoke-s13-hardening.e2e-spec.ts)

## Regra de Manutencao Futura

Para evitar perda de rastreabilidade novamente:

1. Todo sprint novo deve ter pelo menos um artefato nomeado em `docs/architecture/` ou `docs/operations/`.
2. Toda entrega relevante deve ter ao menos um teste nomeado com o padrao `test/smoke-sNN-*.e2e-spec.ts`.
3. Se uma entrega entrar sem documentacao de sprint, registrar temporariamente aqui como `probable`.
4. Quando o sprint ganhar documentacao formal, promover a classificacao para `explicit`.

## Veredito Operacional

O estado atual do `atlas_local` nao para no Sprint 9.

O que esta comprovado no repositorio e:

- base legada equivalente aos Sprints 1 a 4, agora documentada retrospectivamente
- trilha explicita dos Sprints 5 a 8
- camada retrospectiva canonica de Sprint 9
- trilha explicita dos Sprints 10 a 13

Portanto, a leitura mais correta e:

**o atlas_local ja passou do Sprint 9 e hoje apresenta evidencia local de evolucao ate o Sprint 13.**
