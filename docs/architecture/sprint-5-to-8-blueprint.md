<!-- markdownlint-disable MD024 -->
# Blueprint Tecnico - Sprint 5 ao Sprint 8

## Objetivo

Levar o atlas_local do estado atual, que ja possui ingestao, busca, ask, agente ReAct, tracing, context management e guardrails, para uma plataforma hibrida de knowledge agents com:

- supervisor agent
- especialistas por capacidade
- handoffs controlados
- memoria governada
- evals sistematicos
- control tower operacional
- separacao clara entre knowledge plane, agent runtime e control plane

## Sequencia obrigatoria

A ordem abaixo nao e arbitraria. Cada sprint prepara as invariantes do seguinte.

1. Sprint 5
   Estruturar runtime multiagente, registry, handoffs e novas tools basicas.
2. Sprint 6
   Introduzir critic, eval engine, datasets de regressao e qualidade mensuravel.
3. Sprint 7
   Introduzir control plane: dashboards, auditoria, analytics e operacao assistida.
4. Sprint 8
   Consolidar surfaces do produto, hardening, simulacao, readiness e rollout interno.

## Sprint 5 - Multi-agent runtime foundation

### Resultado esperado

Ao fim do Sprint 5, o atlas_local deve conseguir executar um supervisor agent que seleciona agentes especialistas e faz handoff explicito entre eles.

### Objetivos

- Introduzir agent registry.
- Introduzir handoff manager.
- Formalizar agentes especialistas.
- Separar tools por whitelist e ownership.
- Adicionar memoria resumida e identidade de agente por run.

### Ordem exata de implementacao

1. Criar contratos do runtime multiagente.
2. Criar AgentRegistryService.
3. Criar HandoffManagerService.
4. Criar definicoes iniciais de agentes.
5. Adaptar AgentLoopService para operar via supervisor.
6. Introduzir memoria resumida por conversa e por run.
7. Adicionar novas tools internas necessarias ao runtime.
8. Adicionar endpoints de introspeccao do registry.
9. Adicionar testes unitarios e e2e do fluxo de handoff.

### Entregas tecnicas

#### Novos agentes

- supervisor_agent
- knowledge_agent
- extraction_agent
- tool_agent
- critic_agent (stub inicial, sem loop de refinamento ainda)

#### Novos componentes

- AgentRegistryService
- HandoffManagerService
- ConversationMemoryService
- AgentCapability model
- AgentDefinition model

#### Tools minimas adicionais

- extract_structured_data
- get_document_by_id
- summarize_sources
- execute_whitelisted_http_action

### Criterios de aceite

- Um request pode ser roteado do supervisor para pelo menos dois especialistas.
- Cada handoff gera rastros em agent_steps.
- Cada agente so usa tools permitidas para sua definicao.
- O resultado final indica agentes usados e tools usadas.
- O contexto da conversa e resumido sem crescer indefinidamente.

### Testes obrigatorios

- Unit: routing do supervisor por intencao.
- Unit: bloqueio de tool fora da whitelist.
- Unit: handoff manager com cenarios de knowledge, extraction e tools.
- E2E: pergunta documental simples.
- E2E: extracao estruturada.
- E2E: fluxo hibrido knowledge + tool.

### Riscos

- Roteamento heuristico fraco.
- Crescimento de contexto em handoffs.
- Tool sprawl sem ownership claro.

### Mitigacoes

- Comecar com poucas heuristicas e poucos agentes fixos.
- Persistir memoria resumida separada do transcript completo.
- Whitelist por agente desde o primeiro commit.

## Sprint 6 - Quality and evaluation system

### Resultado esperado

Ao fim do Sprint 6, o atlas_local deve ter qualidade mensuravel, regressao detectavel e um critic agent capaz de revisar a saida antes da resposta final.

### Objetivos

- Introduzir evaluation domain.
- Criar datasets de casos canonicos.
- Criar eval engine com score composto.
- Formalizar critic agent.
- Criar simulacao offline de fluxos de agente.

### Ordem exata de implementacao

1. Criar evaluation module e contratos basicos.
2. Criar entidades EvalDataset, EvalCase, EvalRun e EvalScore.
3. Criar EvalEngineService.
4. Criar CriticAgentService.
5. Integrar critic no final do AgentOrchestratorService.
6. Criar dataset inicial de regressao do produto.
7. Criar endpoints para execucao de evals.
8. Criar simulador basico de conversas e runs.
9. Adicionar relatorios persistidos de avaliacao.

### Scores minimos recomendados

- faithfulness
- relevance
- completeness
- citation_coverage
- tool_success
- guardrail_compliance
- latency_budget

### Criterios de aceite

- Existe dataset inicial com pelo menos 25 casos canonicos.
- Cada release local pode rodar evals offline.
- O critic agent consegue revisar drafts e rejeitar saidas sem grounding suficiente.
- Eval runs ficam persistidos no MongoDB.
- Ha comparacao de score entre execucoes.

### Testes obrigatorios

- Unit: score composition.
- Unit: critic rejeita draft sem citacoes quando exigidas.
- E2E: execucao de dataset de regressao.
- E2E: comparacao entre duas eval_runs.

### Riscos

- Score sem utilidade pratica.
- Critic agent excessivamente custoso.
- Datasets artificiais demais.

### Mitigacoes

- Priorizar casos reais do atlas_local.
- Permitir critic curto e barato por padrao.
- Versionar datasets e usar feedback do usuario.

## Sprint 7 - Control plane and operations

### Resultado esperado

Ao fim do Sprint 7, o atlas_local deve ter um control plane minimo com visao operacional da saude do sistema agentic.

### Objetivos

- Introduzir control domain.
- Criar control tower APIs.
- Adicionar analytics de runs, tools, guardrails e latencia.
- Formalizar auditoria de tool execution.
- Introduzir agent registry observavel e versionado.

### Ordem exata de implementacao

1. Criar control module.
2. Criar ControlTowerService.
3. Criar repositorios para aggregates operacionais.
4. Criar metricas de run, tool, guardrail e eval.
5. Criar dashboard API.
6. Criar audit trail para tool executions.
7. Criar agent definition versioning.
8. Criar alertas basicos por thresholds.
9. Criar endpoints de health operacional.

### Visoes minimas do control plane

- runs ativos
- falhas em 24h
- latencia media por agente
- top tools usadas
- guardrail blocks
- score medio das evals
- taxa de handoff por tipo de tarefa

### Criterios de aceite

- E possivel listar a saude operacional do runtime agentic.
- Cada tool execution deixa trilha persistida.
- Cada definicao de agente possui versao e estado ativo.
- E possivel observar degradacao de qualidade por dataset.

### Testes obrigatorios

- Unit: calculo de metricas.
- Unit: agregacao por janela temporal.
- E2E: dashboard API.
- E2E: audit trail de tools.

### Riscos

- Dashboard sem dados uteis.
- Analytics acoplado ao controller.
- Falta de contrato claro entre tracing e operacao.

### Mitigacoes

- Tratar control domain como dominio proprio.
- Reusar agent_runs e agent_steps como fonte canonicа.
- Criar DTOs especificos para consultas operacionais.

## Sprint 8 - Product surfaces, hardening and rollout readiness

### Resultado esperado

Ao fim do Sprint 8, o atlas_local deve estar organizado em surfaces claras do produto, com readiness tecnico para uso interno mais serio.

### Objetivos

- Consolidar surfaces Ask, Extract e Act.
- Adicionar simulation harness.
- Adicionar benchmark e smoke evals obrigatorios.
- Hardening de seguranca e limites operacionais.
- Revisar UX de APIs e contratos.

### Ordem exata de implementacao

1. Separar claramente as superficies do produto.
2. Criar controllers e DTOs especificos para Ask, Extract e Act.
3. Criar simulation harness para cenarios completos.
4. Criar suite de smoke evals obrigatoria para cada release.
5. Endurecer quotas, limites e policies de tools.
6. Revisar erros, fallbacks e timeouts por superficie.
7. Adicionar runbooks operacionais.
8. Executar readiness review e backlog de follow-up.

### Surfaces finais

- Ask
  Resposta com grounding e citacoes.
- Extract
  Saida estruturada validada por schema.
- Act
  Consulta + acao governada por tools aprovadas.

### Criterios de aceite

- As tres superficies possuem contrato proprio.
- Existe smoke suite minima para cada superficie.
- Timeouts e limites sao diferentes por tipo de operacao.
- O rollout interno pode ser auditado e revertido.

### Testes obrigatorios

- E2E: Ask com citacoes.
- E2E: Extract com schema valido.
- E2E: Act com tool success auditado.
- E2E: blocked action por guardrail.

## Dependencias entre sprints

- Sprint 6 depende do registry, handoffs e memoria do Sprint 5.
- Sprint 7 depende de traces e evals persistidos dos Sprints 5 e 6.
- Sprint 8 depende de contratos mais claros e metricas de operacao dos Sprints 6 e 7.

## Definition of done por sprint

Cada sprint so deve ser encerrado quando houver:

- codigo implementado
- testes unitarios
- testes e2e relevantes
- docs atualizadas
- colecoes MongoDB formalizadas quando necessario
- operacao validada com pelo menos um fluxo real do atlas_local

## Recomendacao de corte de escopo

Se for necessario reduzir risco, cortar nesta ordem:

1. simulacao sofisticada do Sprint 8
2. alertas avancados do Sprint 7
3. critic agent com refinamento multiplo no Sprint 6
4. tool diversity no Sprint 5

Nao cortar:

- agent registry
- handoffs
- eval dataset inicial
- audit trail
- separation Ask/Extract/Act
