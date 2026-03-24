# ADR 0001 - Arquitetura-alvo orientada a knowledge agents

- Status: Accepted
- Date: 2026-03-24
- Owners: atlas_local core team

## Contexto

O atlas_local evoluiu de uma base documental local com CLI Python para uma aplicacao hibrida com componentes Python e NestJS no mesmo repositorio. No estado atual, a plataforma ja possui:

- ingestao e indexacao de documentos
- chunking e embedding placeholder
- busca textual e vector search opt-in
- endpoint ask via LLM
- dominio agent com conversas, prompts, tools e loop ReAct
- tracing, context management e guardrails

Apesar disso, o produto ainda nao esta estruturado como uma plataforma de knowledge agents pronta para crescimento funcional. Os principais problemas observados sao:

- ausencia de supervisor agent e handoffs formais
- ausencia de evaluation domain
- ausencia de control plane dedicado
- ausencia de superficies de produto claramente separadas
- governanca parcial sobre memoria, definicoes de agentes e tool execution

O workload assumido para esta decisao e:

- volume inicial pequeno de documentos
- concorrencia baixa no horizonte de 12 meses
- produto hibrido: knowledge engine privado + runtime agentic
- casos de uso principais: perguntas sobre documentos, busca semantica, extracao estruturada, workflows com tools e multiagente

## Decisao

Adotar uma arquitetura-alvo de monolito modular orientado a knowledge agents, separada em tres planos principais:

1. Knowledge plane
   Responsavel por ingestao, normalizacao, chunking, embeddings, retrieval, ranking, citacoes e extracao baseada em documentos.

2. Agent runtime plane
   Responsavel por supervisor, especialistas, handoffs, memoria, contexto, guardrails, tools e consolidacao de resposta.

3. Control plane
   Responsavel por tracing, evals, analytics, auditoria, control tower, health operacional e governanca do runtime.

Essa arquitetura sera implementada incrementalmente entre os Sprints 5 e 8.

## Drivers de decisao

- Evitar microservicos prematuros para um workload ainda pequeno.
- Preservar a estrutura clean architecture ja introduzida em src/domains.
- Elevar o produto de agente funcional para plataforma operavel.
- Tornar qualidade e observabilidade capacidades nativas.
- Manter acoplamento baixo entre knowledge, runtime e operacao.

## Inspiracoes externas traduzidas para o atlas_local

### Glean

Inspira o knowledge plane:

- grounding em conhecimento
- busca contextual
- retrieval como ativo central do produto

### Amazon Bedrock Agents

Inspira o agent runtime:

- supervisor agent
- multi-step execution
- handoffs entre especialistas
- memoria e guardrails integrados

### Kore.ai

Inspira o desenho da plataforma:

- multi-agent orchestration
- observabilidade
- memoria curta e longa
- governanca do runtime

### Intercom Fin

Inspira a operacao da qualidade:

- train, test, deploy, analyze
- simulacao
- melhoria continua baseada em dados

### Moveworks

Inspira o reasoning engine:

- search plus action
- roteamento por capacidade
- selecao do melhor caminho de execucao

### ServiceNow AI Agents

Inspira o control plane:

- control tower
- operacao centralizada
- analise de saude do sistema agentic

## Consequencias positivas

- Arquitetura compativel com o estado atual do repositorio.
- Evolucao incremental e testavel por sprint.
- Melhor separacao entre conhecimento, agente e operacao.
- Base clara para multiagente sem explosao de complexidade.
- Evals e tracing tornam-se pilares de produto.

## Consequencias negativas

- Crescimento do numero de dominios e colecoes.
- Mais contratos e mais disciplina de manutencao.
- Maior investimento inicial em docs, testes e observabilidade.

## Alternativas consideradas

### 1. Permanecer com agente unico baseado em ReAct

Rejeitada porque limita especializacao, observabilidade e evolucao de produto.

### 2. Migrar imediatamente para microservicos

Rejeitada porque aumenta custo operacional antes de haver necessidade real de escala.

### 3. Focar apenas em RAG e nao evoluir o runtime agentic

Rejeitada porque o produto desejado inclui extracao, tools, automacao e multiagente.

## Decisoes estruturais derivadas

1. Manter monolito modular.
2. Introduzir supervisor agent e especialistas fixos.
3. Criar evaluation domain como parte do core, nao como ferramenta externa.
4. Criar control domain com control tower e analytics.
5. Separar superficies de produto em Ask, Extract e Act.
6. Adotar memoria resumida governada em vez de transcript ilimitado.
7. Adotar whitelist de tools por agente.

## Impacto no repositorio

Novos dominios:

- src/domains/evaluation/
- src/domains/control/

Novos componentes centrais:

- AgentRegistryService
- HandoffManagerService
- ConversationMemoryService
- EvalEngineService
- CriticAgentService
- ControlTowerService

Novas colecoes previstas:

- agent_memories
- agent_definitions
- tool_executions
- eval_datasets
- eval_runs
- guardrail_events
- feedback_events

## Estado de adocao

### Ja alinhado com a decisao

- dominio agent
- tracing
- context management
- guardrails
- tool registry

### Ainda faltando para cumprir a decisao

- multi-agent runtime formal
- evaluation domain
- control plane dedicado
- surfaces Ask, Extract e Act

## Plano de implementacao

- Sprint 5: runtime multiagente
- Sprint 6: evaluation system
- Sprint 7: control plane
- Sprint 8: product surfaces e hardening

## Como validar a decisao

A decisao sera considerada bem-sucedida se, ao fim do Sprint 8:

- o atlas_local operar com supervisor e especialistas
- houver datasets de regressao e eval_runs persistidos
- existir control tower com metricas de run e tool execution
- as superficies Ask, Extract e Act estiverem separadas e estaveis
- a qualidade do agente puder ser medida e comparada entre releases
