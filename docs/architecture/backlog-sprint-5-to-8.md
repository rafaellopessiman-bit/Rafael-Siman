<!-- markdownlint-disable MD024 -->
# Backlog Executavel — Sprint 5 a Sprint 8

## Convencao de tickets

- **ID:** `S{sprint}-{sequencia}` — ex: `S5-01`
- **Tipo:** `interface` | `service` | `repository` | `schema` | `tool` | `use-case` | `controller` | `test` | `docs` | `infra`
- **Status:** `todo` | `in-progress` | `done`
- **Desbloqueado por:** IDs que precisam estar `done` antes de comecar

---

## Sprint 5 — Multi-agent runtime foundation

**Objetivo:** Supervisor agent selecionando especialistas com handoff explicito rastreado.

**Criterio de done:** request roteia do supervisor para pelo menos dois especialistas, handoffs persistidos em `agent_steps`, cada agente usa apenas tools da sua whitelist.

### S5-01 — Interface `IAgentCapability`

| Campo | Valor |
| --- | --- |
| Tipo | interface |
| Arquivo | `src/domains/agent/domain/interfaces/agent-capability.interface.ts` |
| Status | done |
| Desbloqueado por | — |

**O que fazer:**

Definir enum `AgentCapability` com valores: `KNOWLEDGE_RETRIEVAL`, `STRUCTURED_EXTRACTION`, `TOOL_EXECUTION`, `CONTENT_CRITIQUE`, `ORCHESTRATION`.

Definir type `AgentCapabilitySet = Set<AgentCapability>`.

---

### S5-02 — Interface `IAgentHandoff`

| Campo | Valor |
| --- | --- |
| Tipo | interface |
| Arquivo | `src/domains/agent/domain/interfaces/agent-handoff.interface.ts` |
| Status | done |
| Desbloqueado por | S5-01 |

**O que fazer:**

Definir `IAgentHandoff` com campos: `fromAgent: string`, `toAgent: string`, `reason: string`, `contextSummary: string`, `timestamp: Date`.

Definir `HandoffDecision` com `targetAgentId: string`, `reason: string`, `requiresContext: boolean`.

---

### S5-03 — Interface `IAgentDefinition`

| Campo | Valor |
| --- | --- |
| Tipo | interface |
| Arquivo | `src/domains/agent/domain/interfaces/agent-definition.interface.ts` |
| Status | done |
| Desbloqueado por | S5-01 |

**O que fazer:**

Definir `IAgentDefinition` com: `id: string`, `name: string`, `description: string`, `version: string`, `capabilities: AgentCapability[]`, `allowedTools: string[]`, `handoffTargets: string[]`, `systemPrompt: string`, `isActive: boolean`.

---

### S5-04 — Schema `AgentDefinition` (Mongoose)

| Campo | Valor |
| --- | --- |
| Tipo | schema |
| Arquivo | `src/domains/agent/infrastructure/persistence/agent-definition.schema.ts` |
| Status | done |
| Desbloqueado por | S5-03 |

**O que fazer:**

Schema Mongoose com campos de `IAgentDefinition` + `createdAt`, `updatedAt`, `schemaVersion: 1`. Collection name: `agent_definitions`.

---

### S5-05 — Schema `AgentMemory` (Mongoose)

| Campo | Valor |
| --- | --- |
| Tipo | schema |
| Arquivo | `src/domains/agent/infrastructure/persistence/agent-memory.schema.ts` |
| Status | done |
| Desbloqueado por | — |

**O que fazer:**

Schema com: `conversationId: string`, `agentId: string`, `summary: string`, `keyFacts: string[]`, `runIds: string[]`, `createdAt`, `updatedAt`, `schemaVersion: 1`. Collection: `agent_memories`.

---

### S5-06 — Repository interface `IAgentDefinitionRepository`

| Campo | Valor |
| --- | --- |
| Tipo | repository |
| Arquivo | `src/domains/agent/domain/repositories/agent-definition.repository.interface.ts` |
| Status | done |
| Desbloqueado por | S5-03 |

**O que fazer:**

Interface com: `findById(id: string)`, `findAll()`, `findActive()`, `upsert(def: IAgentDefinition)`. Token symbol `AGENT_DEFINITION_REPOSITORY`.

---

### S5-07 — Repository interface `IAgentMemoryRepository`

| Campo | Valor |
| --- | --- |
| Tipo | repository |
| Arquivo | `src/domains/agent/domain/repositories/agent-memory.repository.interface.ts` |
| Status | done |
| Desbloqueado por | S5-05 |

**O que fazer:**

Interface com: `findByConversationAndAgent(conversationId, agentId)`, `upsert(memory)`, `findRecent(conversationId, limit)`. Token symbol `AGENT_MEMORY_REPOSITORY`.

---

### S5-08 — Repository impl `MongooseAgentDefinitionRepository`

| Campo | Valor |
| --- | --- |
| Tipo | repository |
| Arquivo | `src/domains/agent/infrastructure/persistence/agent-definition.repository.ts` |
| Status | done |
| Desbloqueado por | S5-04, S5-06 |

**O que fazer:**

Implementacao Mongoose de `IAgentDefinitionRepository`. `findActive()` filtra `isActive: true`.

---

### S5-09 — Repository impl `MongooseAgentMemoryRepository`

| Campo | Valor |
| --- | --- |
| Tipo | repository |
| Arquivo | `src/domains/agent/infrastructure/persistence/agent-memory.repository.ts` |
| Status | done |
| Desbloqueado por | S5-05, S5-07 |

**O que fazer:**

Implementacao Mongoose com upsert por `conversationId + agentId`. `findRecent` ordena por `createdAt desc` com limit.

---

### S5-10 — `AgentRegistryService`

| Campo | Valor |
| --- | --- |
| Tipo | service |
| Arquivo | `src/domains/agent/domain/services/agent-registry.service.ts` |
| Status | done |
| Desbloqueado por | S5-06, S5-08 |

**O que fazer:**

Service com cache in-memory `Map<string, IAgentDefinition>`. Metodos: `register(def)`, `get(id)`, `getAll()`, `getActive()`, `isToolAllowed(agentId, toolName): boolean`. `OnModuleInit` carrega definicoes do banco. Exporta para o modulo.

---

### S5-11 — `HandoffManagerService`

| Campo | Valor |
| --- | --- |
| Tipo | service |
| Arquivo | `src/domains/agent/domain/services/handoff-manager.service.ts` |
| Status | done |
| Desbloqueado por | S5-02, S5-10 |

**O que fazer:**

Service com: `decide(currentAgentId, userIntent, context): HandoffDecision`. Logica: verifica `handoffTargets` do agente atual, seleciona por keywords de intent (knowledge → knowledge_agent, extract → extraction_agent, tool/action → tool_agent). `execute(decision, runId, stepCounter): void` persiste o handoff como step tipo `handoff` no TracingService.

---

### S5-12 — `ConversationMemoryService`

| Campo | Valor |
| --- | --- |
| Tipo | service |
| Arquivo | `src/domains/agent/domain/services/conversation-memory.service.ts` |
| Status | done |
| Desbloqueado por | S5-07, S5-09 |

**O que fazer:**

Service com: `getMemory(conversationId, agentId): AgentMemory | null`, `updateMemory(conversationId, agentId, newFacts: string[], runId: string): void`, `buildContextSummary(conversationId, agentId): string`. O summary e usado como injecao no system prompt do agente.

---

### S5-13 — Definicoes default de agentes

| Campo | Valor |
| --- | --- |
| Tipo | infra |
| Arquivo | `src/domains/agent/infrastructure/registry/default-agent-definitions.ts` |
| Status | done |
| Desbloqueado por | S5-03 |

**O que fazer:**

Exportar array `DEFAULT_AGENT_DEFINITIONS: IAgentDefinition[]` com 5 entradas:

- `supervisor_agent` — capabilities: `[ORCHESTRATION]`, allowedTools: todos, handoffTargets: todos os outros
- `knowledge_agent` — capabilities: `[KNOWLEDGE_RETRIEVAL]`, allowedTools: `[search_documents, list_sources, get_cached_answer, get_document_by_id, summarize_sources]`
- `extraction_agent` — capabilities: `[STRUCTURED_EXTRACTION]`, allowedTools: `[search_documents, get_document_by_id, extract_structured_data]`
- `tool_agent` — capabilities: `[TOOL_EXECUTION]`, allowedTools: `[execute_whitelisted_http_action, list_sources]`
- `critic_agent` — capabilities: `[CONTENT_CRITIQUE]`, allowedTools: `[search_documents]`

---

### S5-14 — `AgentOrchestratorService`

| Campo | Valor |
| --- | --- |
| Tipo | service |
| Arquivo | `src/domains/agent/domain/services/agent-orchestrator.service.ts` |
| Status | done |
| Desbloqueado por | S5-10, S5-11, S5-12 |

**O que fazer:**

Service principal do Sprint 5. Metodo `orchestrate(conversationId, messages, options)`. Fluxo:

1. Carrega memoria da conversa via `ConversationMemoryService`
2. Supervisor seleciona agente especialista inicial via `HandoffManagerService`
3. Executa `AgentLoopService.run()` com ferramentas filtradas pela whitelist do agente
4. Se especialista pede handoff (keyword `[HANDOFF:agentId]` no output), troca de agente
5. Persiste handoff via TracingService como step `handoff`
6. Atualiza memoria ao final via `ConversationMemoryService`
7. Retorna resultado com `agentsUsed[]` e `handoffCount`

---

### S5-15 — Tool `extract-structured-data`

| Campo | Valor |
| --- | --- |
| Tipo | tool |
| Arquivo | `src/domains/agent/infrastructure/tools/extract-structured-data.tool.ts` |
| Status | done |
| Desbloqueado por | S5-01 |

**O que fazer:**

Tool que recebe `query: string`, `schema: string` (JSON Schema como string), `sourceIds?: string[]`. Busca documentos e pede ao LLM para extrair campos seguindo o schema. Retorna JSON stringificado.

---

### S5-16 — Tool `get-document-by-id`

| Campo | Valor |
| --- | --- |
| Tipo | tool |
| Arquivo | `src/domains/agent/infrastructure/tools/get-document-by-id.tool.ts` |
| Status | done |
| Desbloqueado por | — |

**O que fazer:**

Tool com parametro `documentId: string`. Busca documento por ID no `KnowledgeRepository`. Retorna `title`, `content` (primeiros 3000 chars) e `sourceFile`.

---

### S5-17 — Tool `summarize-sources`

| Campo | Valor |
| --- | --- |
| Tipo | tool |
| Arquivo | `src/domains/agent/infrastructure/tools/summarize-sources.tool.ts` |
| Status | done |
| Desbloqueado por | — |

**O que fazer:**

Tool com parametro `query: string`, `maxSources?: number`. Busca top-N documentos e retorna lista de fontes com titulo, trecho e score de relevancia. Util para o critic e para citacoes.

---

### S5-18 — Use case `RunAgentOrchestratorUseCase`

| Campo | Valor |
| --- | --- |
| Tipo | use-case |
| Arquivo | `src/domains/agent/application/use-cases/run-agent-orchestrator.use-case.ts` |
| Status | done |
| Desbloqueado por | S5-14 |

**O que fazer:**

Use case que recebe `conversationId` e `SendMessageDto`, carrega historico da conversa, chama `AgentOrchestratorService.orchestrate()`, salva nova mensagem do assistente no historico, retorna resultado enriquecido com `agentsUsed`, `handoffCount`, `toolsUsed`.

---

### S5-19 — Endpoint `GET /agent/registry`

| Campo | Valor |
| --- | --- |
| Tipo | controller |
| Arquivo | `src/domains/agent/infrastructure/http/agent.controller.ts` (modificar) |
| Status | done |
| Desbloqueado por | S5-10 |

**O que fazer:**

Adicionar endpoint `GET /agent/registry` que retorna lista de agentes ativos com suas capabilities e allowedTools. Adicionar `GET /agent/registry/:id` para detalhe de um agente.

---

### S5-20 — Atualizar `agent.module.ts`

| Campo | Valor |
| --- | --- |
| Tipo | infra |
| Arquivo | `src/domains/agent/agent.module.ts` (modificar) |
| Status | done |
| Desbloqueado por | S5-08, S5-09, S5-10, S5-11, S5-12, S5-14, S5-18 |

**O que fazer:**

Registrar no modulo: novos schemas (`AgentDefinition`, `AgentMemory`), novos repositories, `AgentRegistryService`, `HandoffManagerService`, `ConversationMemoryService`, `AgentOrchestratorService`, `RunAgentOrchestratorUseCase`, novas tools.

---

### S5-21 — Atualizar `mongo-init-scripts/01-init-db.js`

| Campo | Valor |
| --- | --- |
| Tipo | infra |
| Arquivo | `mongo-init-scripts/01-init-db.js` (modificar) |
| Status | done |
| Desbloqueado por | S5-04, S5-05 |

**O que fazer:**

Adicionar criacao das collections `agent_definitions` e `agent_memories` com indexes: `agent_definitions.id` (unique), `agent_memories (conversationId + agentId)` (unique compound).

---

### S5-22 — Testes unitarios Sprint 5

| Campo | Valor |
| --- | --- |
| Tipo | test |
| Arquivo | `test/agent/agent-registry.spec.ts`, `test/agent/handoff-manager.spec.ts`, `test/agent/conversation-memory.spec.ts` |
| Status | done |
| Desbloqueado por | S5-10, S5-11, S5-12 |

**O que fazer:**

- `agent-registry.spec.ts`: isToolAllowed retorna true/false correto; get retorna definicao registrada.
- `handoff-manager.spec.ts`: decide retorna knowledge_agent para query documental; decide retorna extraction_agent para query com "extraia"; bloqueio por ferramenta fora da whitelist.
- `conversation-memory.spec.ts`: upsert cria nova memoria; segunda chamada atualiza existente.

---

### S5-23 — Teste E2E — Fluxo multiagente

| Campo | Valor |
| --- | --- |
| Tipo | test |
| Arquivo | `test/agent-orchestrator.e2e-spec.ts` |
| Status | done |
| Desbloqueado por | S5-18, S5-20 |

**O que fazer:**

- Criar conversa, enviar pergunta documental → resposta com `agentsUsed` incluindo `knowledge_agent`.
- Enviar pergunta de extracao → resposta com `agentsUsed` incluindo `extraction_agent`.
- Verificar que `handoffCount >= 0` esta presente no response body.

---

## Sprint 6 — Quality and evaluation system

**Objetivo:** Qualidade mensuravel com eval runs persistidos e critic agent ativo no fluxo.

**Status: DONE** — Todos os tickets implementados e testados (65 e2e tests passing).

| ID | Arquivo | Descricao | Status |
| --- | --- | --- | --- |
| S6-01 | `src/domains/evaluation/evaluation.module.ts` | Criar modulo NestJS do dominio evaluation | done |
| S6-02 | `src/domains/evaluation/domain/interfaces/eval-dataset.interface.ts` | Interface EvalDataset | done |
| S6-03 | `src/domains/evaluation/domain/interfaces/eval-case.interface.ts` | Interface EvalCase com input/expected/actual | done |
| S6-04 | `src/domains/evaluation/domain/interfaces/eval-run.interface.ts` | EvalRun com status, scores e duracao | done |
| S6-05 | `src/domains/evaluation/domain/interfaces/eval-score.interface.ts` | Score composto (faithfulness, relevance, etc.) | done |
| S6-06 | `src/domains/evaluation/infrastructure/persistence/*.ts` | Schemas e repos Mongoose | done |
| S6-07 | `src/domains/evaluation/domain/services/eval-engine.service.ts` | Engine que calcula scores | done |
| S6-08 | `src/domains/evaluation/domain/services/critic-agent.service.ts` | Critic integrado ao AgentOrchestrator | done |
| S6-09 | `src/domains/evaluation/data/core-regression.dataset.ts` | Dataset com 25 casos canonicos | done |
| S6-10 | `src/domains/evaluation/infrastructure/http/evaluation.controller.ts` | Endpoints: POST /eval/run, GET /eval/runs | done |
| S6-11 | `test/evaluation.e2e-spec.ts` | E2E: rodar dataset, comparar eval_runs | done |

---

## Sprint 7 — Control plane and operations

**Objetivo:** Dashboard operacional do runtime agentic com audit de tool executions.

**Status: DONE** — Todos os tickets implementados e testados (69 e2e tests passing).

| ID | Arquivo | Descricao | Status |
| --- | --- | --- | --- |
| S7-01 | `src/domains/control/control.module.ts` | Criar modulo NestJS do dominio control | done |
| S7-02 | `src/domains/control/domain/services/control-tower.service.ts` | Agregacao de metricas de runs, tools, guardrails | done |
| S7-03 | `src/domains/control/infrastructure/persistence/tool-execution.schema.ts` | Schema dedicado para tool executions | done |
| S7-04 | `src/domains/control/infrastructure/http/control.controller.ts` | GET /control/dashboard, GET /control/health | done |
| S7-05 | `src/domains/control/domain/services/agent-versioning.service.ts` | Versionamento de AgentDefinition | done |
| S7-06 | `src/domains/control/domain/services/alert.service.ts` | Alertas por threshold (latencia, guardrail blocks) | done |
| S7-07 | `test/control.e2e-spec.ts` | E2E: dashboard API, audit trail de tools | done |

---

## Sprint 8 — Product surfaces, hardening and rollout readiness

**Objetivo:** Surfaces Ask/Extract/Act com contratos proprios, smoke evals e runbooks.

**Status: DONE** — Todos os tickets implementados e testados (72 e2e tests passing).

**Tickets resumidos:**

| ID | Arquivo | Descricao | Status |
| --- | --- | --- | --- |
| S8-01 | `src/domains/agent/infrastructure/http/ask.controller.ts` | Surface Ask: POST /ask com grounding e citacoes | done |
| S8-02 | `src/domains/agent/infrastructure/http/extract.controller.ts` | Surface Extract: POST /extract com schema | done |
| S8-03 | `src/domains/agent/infrastructure/http/act.controller.ts` | Surface Act: POST /act com tools governadas | done |
| S8-04 | `src/domains/agent/application/dtos/ask.dto.ts` | DTO especifico com fields: query, topK, citationMode | done |
| S8-05 | `src/domains/agent/application/dtos/extract.dto.ts` | DTO com fields: query, outputSchema, sourceIds | done |
| S8-06 | `src/domains/agent/application/dtos/act.dto.ts` | DTO com fields: intent, allowedActions, contextId | done |
| S8-07 | `test/smoke-ask.e2e-spec.ts` | Smoke suite Ask obrigatoria | done |
| S8-08 | `test/smoke-extract.e2e-spec.ts` | Smoke suite Extract obrigatoria | done |
| S8-09 | `test/smoke-act.e2e-spec.ts` | Smoke suite Act com tool auditada | done |
| S8-10 | `docs/operations/agent-runtime-runbook.md` | Runbook operacional do runtime | done |
| S8-11 | `docs/operations/evaluation-runbook.md` | Runbook de avaliacao continua | done |

---

## Ordem de implementacao global (dependencias entre sprints)

```text
S5-01 → S5-02, S5-03
S5-03 → S5-04, S5-06, S5-13
S5-04, S5-06 → S5-08
S5-05, S5-07 → S5-09
S5-10 → S5-11, S5-19
S5-11, S5-12 → S5-14
S5-14 → S5-18
S5-18, S5-20 → S5-22, S5-23

S5-done → S6-01 ... S6-11

S6-done → S7-01 ... S7-07

S7-done → S8-01 ... S8-11
```
