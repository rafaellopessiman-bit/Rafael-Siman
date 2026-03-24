<!-- markdownlint-disable MD024 -->
# Gap Analysis - Estado Atual vs Arquitetura-Alvo

## Resumo executivo

O atlas_local ja possui uma base tecnica melhor do que um prototipo comum. Ha ingestao, busca, LLM ask, dominio agent com loop ReAct, tracing, context management e guardrails.

O gap principal nao esta em "ter um agente". O gap principal esta em transformar o sistema em uma plataforma de knowledge agents com:

- supervisor e especialistas
- memoria governada
- evals sistematicos
- control plane
- surfaces de produto claras

## Estado atual confirmado

### Existe hoje

- dominio knowledge com indexacao, chunking, embedding placeholder e busca
- dominio llm com ask e cache
- dominio agent com conversas, prompts, tools, loop ReAct, tracing e guardrails
- dominio planner e tabular
- collections conversations, prompt_templates, agent_runs e agent_steps
- 81 testes Python passando

### Nao existe hoje

- evaluation domain
- control domain
- supervisor agent formal
- handoff manager formal
- registry versionado de agentes
- critic agent
- dataset de regressao persistido
- control tower
- audit trail dedicado para tool execution
- superficies Ask, Extract e Act separadas

## Gaps por capacidade

### 1. Product architecture gap

#### Estado atual

O produto ainda esta organizado mais por funcionalidades tecnicas do que por superficies finais de uso.

#### Alvo

Separar o produto em Ask, Extract e Act.

#### Impacto

- contratos mais claros
- timeouts e quotas especificos
- melhor UX de API

#### Prioridade

Alta, Sprint 8.

### 2. Multi-agent runtime gap

#### Estado atual

Existe loop ReAct com tools, mas nao ha supervisor agent nem handoffs explicitos entre especialistas.

**Atendimento parcial confirmado (evidencias no codigo):**

- `src/domains/agent/domain/services/agent-loop.service.ts` — loop ReAct completo com MAX_ITERATIONS=8, execucao paralela de tool_calls via Promise.all, guardrail de input/output integrado. O loop existe mas opera como agente unico sem delegar para especialistas.
- `src/domains/agent/domain/interfaces/agent-tool.interface.ts` — contrato `IAgentTool` com `name`, `description`, `parameters`, `execute()`. Base reutilizavel para contratos de agente.
- `src/domains/agent/infrastructure/tools/search-documents.tool.ts`, `list-sources.tool.ts`, `get-cached-answer.tool.ts` — tools registradas e funcionais. Provam que o mecanismo de dispatch ja funciona.
- Endpoint ativo: `POST /agent/conversations/:id/messages` — entrypoint do loop.

**Gap restante:** sem `AgentOrchestratorService`, sem supervisor, sem handoff explicito de especialistas.

#### Alvo

Runtime com supervisor_agent, knowledge_agent, extraction_agent, tool_agent e critic_agent.

#### Impacto

- respostas mais especializadas
- melhor composicao de workflows
- base para escalabilidade funcional

#### Prioridade

Altissima, Sprint 5.

### 3. Agent registry gap

#### Estado atual

Ha registry de tools, mas nao ha registry formal de agentes com capacidades, ferramentas permitidas e destinos de handoff.

**Atendimento parcial confirmado (evidencias no codigo):**

- `src/domains/agent/domain/services/tool-registry.service.ts` — `ToolRegistryService` com `Map<string, IAgentTool>`, `register()`, `get()`, `getAll()`, `toGroqTools()`, `dispatch()`. Padrao de registry ja implementado para tools, pronto para ser espelhado em `AgentRegistryService`.
- Endpoint ativo: `GET /agent/tools` — lista tools registradas. Prova da introspeccao do registry.
- Endpoint ativo: `GET /agent/guardrails` — lista guardrails ativos.

**Gap restante:** nao ha `AgentDefinition` com `capabilities`, `allowedTools`, `handoffTargets`. O registry e exclusivo de tools.

#### Alvo

AgentRegistryService com definicoes versionadas.

#### Impacto

- governanca
- previsibilidade
- introspeccao do runtime

#### Prioridade

Altissima, Sprint 5.

### 4. Memory gap

#### Estado atual

Ha context management, mas ainda nao ha memoria governada de longo prazo por conversa e por run.

**Atendimento parcial confirmado (evidencias no codigo):**

- `src/domains/agent/domain/services/context-manager.service.ts` — `ContextManagerService` com sliding window (40 msgs), tool output trimming (2000 chars), token estimation e injecao de resumo de contexto descartado. Gerencia o short-term context eficientemente.
- `src/domains/agent/infrastructure/persistence/conversation.schema.ts` e `conversation.repository.ts` — historico completo persistido por conversa no MongoDB.
- `src/domains/agent/infrastructure/persistence/agent-run.schema.ts` — cada run tem `conversationId`, `totalIterations`, `toolsUsed`, `finalAnswer`.

**Gap restante:** nao ha `ConversationMemoryService` com resumos de longo prazo, sem collection `agent_memories`, sem consulta seletiva de memorias passadas entre runs distintos de uma mesma conversa.

#### Alvo

ConversationMemoryService com memoria resumida, consulta seletiva e persistencia controlada.

#### Impacto

- menos inflacao de contexto
- maior continuidade
- melhor custo previsivel

#### Prioridade

Alta, Sprint 5.

### 5. Evaluation gap

#### Estado atual

Nao existe dominio de avaliacao. O sistema nao mede faithfulness, relevance, completeness ou tool success de forma persistida.

#### Alvo

Evaluation module com datasets, eval runs, scores e simulacao.

#### Impacto

- regressao detectavel
- qualidade mensuravel
- melhoria continua baseada em evidencia

#### Prioridade

Altissima, Sprint 6.

### 6. Critic gap

#### Estado atual

Nao ha agente critico revisando a saida antes da resposta final.

#### Alvo

CriticAgentService avaliando grounding, completude e aderencia a regras.

#### Impacto

- menos alucinacao
- resposta final mais consistente

#### Prioridade

Alta, Sprint 6.

### 7. Control plane gap

#### Estado atual

Ha tracing granular, mas nao ha camada dedicada para visualizacao operacional e agregacao de metricas.

#### Alvo

Control module com control tower, analytics e snapshot operacional.

#### Impacto

- operacao auditavel
- diagnostico rapido
- readiness para uso serio

#### Prioridade

Altissima, Sprint 7.

### 8. Tool execution audit gap

#### Estado atual

Tool calls aparecem em agent_steps, mas nao ha trilha especializada com semantica operacional propria.

#### Alvo

tool_executions ou equivalente com status, inputs saneados, outputs resumidos, latencia e ownership.

#### Impacto

- auditoria
- custo por tool
- analise de falhas

#### Prioridade

Alta, Sprint 7.

### 9. Knowledge plane depth gap

#### Estado atual

Knowledge domain ainda mistura chunk canonicо e unidade de busca na mesma estrutura principal. Retrieval existe, mas sem uma camada dedicada de ranking e sem colecoes separadas para chunks e memorias.

#### Alvo

Knowledge plane com distinction clara entre documento canonico, chunk e index de busca.

#### Impacto

- evolucao mais segura do retrieval
- tuning mais fino
- melhor observabilidade de ranking

#### Prioridade

Media-alta, Sprint 6 e Sprint 7.

### 10. API surface gap

#### Estado atual

As APIs ainda sao muito centradas em dominio tecnico e menos em jobs do usuario final.

#### Alvo

Superficies explicitas:

- POST /ask
- POST /extract
- POST /act

#### Impacto

- clareza do contrato
- seguranca e quotas por tipo de operacao

#### Prioridade

Alta, Sprint 8.

## Gaps por dominio

| Dominio alvo | Estado atual | Gap | Prioridade |
| --- | --- | --- | --- |
| knowledge | existe | aprofundar separacao documento, chunk e retrieval | media-alta |
| agent | existe | adicionar supervisor, handoff, registry, memoria | altissima |
| evaluation | nao existe | criar do zero | altissima |
| control | nao existe | criar do zero | altissima |
| integrations | parcial e disperso | consolidar ownership e contracts | alta |

## Gaps por colecao

| Colecao alvo | Situacao atual |
| --- | --- |
| knowledge_documents | existe |
| knowledge_chunks | nao existe |
| embeddings_index | nao existe |
| conversations | existe |
| prompt_templates | existe |
| agent_runs | existe |
| agent_steps | existe |
| agent_memories | nao existe |
| agent_definitions | nao existe |
| tool_executions | nao existe |
| eval_datasets | nao existe |
| eval_runs | nao existe |
| guardrail_events | nao existe |
| feedback_events | nao existe |
| search_logs | parcial, hoje query logs vivem no dominio llm |

## Gaps por operacao

### Hoje

- tracing existe
- guardrails existem
- tools existem
- ask existe

### Faltando

- run quality score
- offline regression suite
- runtime control tower
- simulation harness
- agent policy versioning
- audit de tool ownership

## Roadmap recomendado de fechamento de gaps

### Sprint 5

Fechar gaps 2, 3 e 4.

### Sprint 6

Fechar gaps 5, 6 e parte do 9.

### Sprint 7

Fechar gaps 7, 8 e consolidar metricas do 9.

### Sprint 8

Fechar gap 10 e consolidar rollout readiness.

## Conclusao

O atlas_local nao esta atras em fundamentos. Ele esta numa transicao critica entre:

- agente funcional de primeira geracao
- plataforma agentic operavel e mensuravel

O caminho certo nao e adicionar mais features soltas. O caminho certo e estruturar as capacidades faltantes em torno de quatro pilares:

1. multi-agent runtime
2. evaluation system
3. control plane
4. product surfaces claras

Esse e o delta real entre o estado atual e a arquitetura-alvo.
