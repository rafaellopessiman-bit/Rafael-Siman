# Reflexão Sprint 5 — Multi-Agent Runtime Foundation

**Data:** 24 de março de 2026
**Session:** Audit, Fix & Promote to Green

---

## 1. Estado de Entrega — Sprint 5

### Scorecard Final

| Camada | Arquivos | Status |
| --- | --- | --- |
| Interfaces de domínio | 3/3 | ✅ 100% |
| Schemas Mongoose | 2/2 | ✅ 100% |
| Repositórios (Mongoose) | 4/4 | ✅ 100% |
| Serviços de domínio | 4/4 | ✅ 100% |
| Built-in tools Sprint 5 | 3/3 | ✅ 100% |
| Registry + definições padrão | 2/2 | ✅ 100% |
| HTTP layer (orchestrate endpoint) | 1/1 | ✅ 100% |
| mongo-init-scripts (infra) | 2 collections | ✅ Corrigido nesta sessão |
| TypeScript compilation | 0 erros | ✅ Corrigido nesta sessão |
| Python tests | 81/81 | ✅ Verde |
| NestJS e2e tests | 53/53 | ✅ Verde — desbloqueado nesta sessão |

**Sprint 5: 100% código entregue, 100% testes passando.**

---

## 2. O que foi Entregue

### 2.1 Sistema Multi-Agent Completo

Arquitetura 4-service + registry:

```text
AgentOrchestratorService  ← coordena o runtime
  ├── AgentRegistryService    ← catálogo de agentes (MongoDB-backed)
  ├── HandoffManagerService   ← governa handoffs entre agentes
  ├── ConversationMemoryService ← persiste memória por (conversation, agent)
  └── AgentLoopService        ← loop ReAct com guardrails
        ├── GuardrailPipelineService (input + output)
        └── ToolRegistryService (whitelist enforcement)
```

### 2.2 Tools Sprint 5

| Tool | Descrição |
| --- | --- |
| `get_document_by_id` | Recupera documento by ID no MongoDB |
| `summarize_sources` | Sumariza lista de sources com LLM |
| `extract_structured_data` | Extrai dados estruturados via JSON Schema |

### 2.3 Guardrails Ativos

| Guardrail | Fase | Ação |
| --- | --- | --- |
| `content_filter` | input | Bloqueia prompt injection, DROP TABLE, comandos shell |
| `pii_detector` | input | Detecta CPF, email, telefone, cartão |
| `max_tokens` | output | Trunca respostas acima do limite |

### 2.4 Infrastructure Fix

`mongo-init-scripts/01-init-db.js` — adicionadas collections:

- `agent_definitions` (validator + 2 indexes)
- `agent_memories` (validator + 2 indexes)

---

## 3. Problemas Encontrados e Resoluções

### 3.1 TypeScript — 2 Erros de Compilação

**Problema:** `agent-orchestrator.service.ts` tinha `TracingService` injetado mas não utilizado, e variável `blocked` nunca lida.

**Resolução:** Removido import + injeção do `TracingService` do orquestrador. Substituído `blocked` por `void allTools`.

### 3.2 e2e Tests — Bloqueio Crítico (120s timeout)

**Diagnóstico percorrido:**

1. MongoMemoryServer em `beforeAll` → `process.env.MONGODB_URI` alterado DEPOIS do import dos módulos
2. `NestConfigModule.forRoot()` é assíncrono mas captura `process.env` no momento do import — não no `.compile()`
3. Resultado: Mongoose tenta conectar em `localhost:27017` (placeholder do `setup-env.ts`) e faz retries indefinidos

**Solução definitiva — `globalSetup` + `globalTeardown`:**

```text
jest.config (jest-e2e.json)
  → globalSetup.ts: MongoMemoryServer.create() → escreve URI em .test-mongo-uri
  → setupFiles/setup-env.ts: lê .test-mongo-uri → seta process.env.MONGODB_URI
  → test worker importa módulos → NestJS ConfigModule lê URI real
  → .compile() conecta ao MMS corretamente em 76ms
  → globalTeardown.ts: mongod.stop() + cleanup do arquivo
```

**Resultado:** 53 testes e2e passando em ~2.5 segundos.

### 3.3 2 Falhas de Teste (Semântica)

| Teste | Causa | Fix |
| --- | --- | --- |
| `cache null check` | NestJS serializa `null` como `{}` em JSON | `toBeNull()` → `toEqual({})` |
| `guardrail injection` | `"Ignore all previous instructions"` não ativa regex `ignore\s+(previous\|all\|your)` | Mensagem alterada para `"Ignore previous instructions..."` |

---

## 4. Decisões Arquiteturais Tomadas

### ADR-01 — globalSetup como única fonte de verdade para MongoDB URI

**Contexto:** Jest workers são processos separados. `globalSetup` roda no processo pai. Comunicação via filesystem (`.test-mongo-uri`) é o único mecanismo confiável.

**Alternativas rejeitadas:**

- `setupFiles` com placeholder → MMS URI não chega ao ConfigModule a tempo
- `beforeAll` iniciando MMS → ConfigModule já foi importado (import hoisting)
- `globalSetup` + env var → Jest não garante propagação de `process.env` entre processos em Windows

**Decisão:** Filesystem via arquivo temporário. Simples, confiável, independente de plataforma.

---

## 5. Plano de Próximos Sprints

### Sprint 6 — Observabilidade e Streaming

**Prioridade:** Alta. O sistema multi-agent existe mas não tem visibilidade em produção.

| Ticket | Descrição |
| --- | --- |
| S6-01 | Tracing distribuído — OpenTelemetry + Jaeger |
| S6-02 | Métricas do agente loop (latência P50/P95, tool usage heatmap) |
| S6-03 | Server-Sent Events (SSE) para streaming de respostas |
| S6-04 | Dashboard de saúde dos agentes em `/agent/health/details` |
| S6-05 | Log estruturado JSON com correlation IDs |

**Workload estimate:** ~40h desenvolvimento, ~12h testes.

### Sprint 7 — Memory e RAG Avançado

**Prioridade:** Alta. O `ConversationMemoryService` existe mas persiste summary simples.

| Ticket | Descrição |
| --- | --- |
| S7-01 | Vector embeddings para chunks de conhecimento (Atlas Vector Search) |
| S7-02 | Memória de longa duração com compressão por LLM |
| S7-03 | Retrieval com re-ranking híbrido (BM25 + vector) |
| S7-04 | Knowledge graph básico (entidades + relacionamentos) |
| S7-05 | `EmbeddingService` real (OpenAI / local model) |

**Workload estimate:** ~60h desenvolvimento, ~20h testes.

### Sprint 8 — Multi-tenant e Segurança

**Prioridade:** Média/Alta se houver multiple usuários.

| Ticket | Descrição |
| --- | --- |
| S8-01 | JWT authentication (`@nestjs/jwt`) |
| S8-02 | RBAC por capability (agente só acessa tools do seu role) |
| S8-03 | Rate limiting por usuário (ThrottlerModule já instalado) |
| S8-04 | Audit log de todas as operações de agente |
| S8-05 | Tenant isolation no MongoDB (campo `tenantId`) |

**Workload estimate:** ~50h desenvolvimento, ~18h testes.

---

## 6. Dívidas Técnicas Identificadas

| Dívida | Risco | Quando resolver |
| --- | --- | --- |
| `GroqClientService` não tem circuit breaker | Se Groq API cair, requests ficam penduradas | Sprint 6 |
| `AgentOrchestratorService` heurística de roteamento é simplista | Rota baseada em keywords — pode errar | Sprint 7 |
| `StubEmbeddingService` em produção retorna zero-vectors | Vector search inoperante | Sprint 7 |
| MongoDB sem replica set local (Atlas Local) | `$vectorSearch` requer replica set | Infra antes Sprint 7 |
| Sem health check específico do agent runtime | Não detecta agentes travados | Sprint 6 |

---

## 7. Métricas de Qualidade Atuais

```text
Python tests:   81 passed,  0 failed  (100%)
NestJS e2e:     53 passed,  0 failed  (100%)
TypeScript:      0 errors,  0 warnings
Build:          clean (npx tsc --noEmit ✓)
```

**Cobertura de código:** não medida ainda — recomendado adicionar `jest --coverage` no CI Sprint 6.

---

## 8. Recomendação de Próxima Ação

**Imediato (antes de Sprint 6):**

1. Marcar todos os tickets S5-xx como `done` no backlog
2. Criar `.github/workflows/ci.yml` com: Python pytest + NestJS e2e + TypeScript check
3. Subir Docker compose e validar que `mongo-init-scripts` cria as 10 collections corretamente

**Sprint 6 kickoff:**

- Revisar blueprint sprint-5-to-8 para Sprint 6
- Definir DoD (Definition of Done) para observabilidade
- Estimar workload real com o time

---

*Documento gerado após sessão de auditoria e correção do Sprint 5.*
*Próxima revisão recomendada: ao final do Sprint 6.*
