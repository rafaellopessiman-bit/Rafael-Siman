<!-- markdownlint-disable MD024 -->
# Estrutura Concreta de Pastas e Arquivos

## Objetivo

Este documento descreve a estrutura-alvo do repositorio para suportar a arquitetura de knowledge agents do atlas_local sem quebrar a base atual.

## Principio de evolucao

Nao reorganizar tudo de uma vez. Introduzir novos dominios e componentes por camada, preservando compatibilidade com a estrutura atual em src/domains.

## Estrutura-alvo

```text
docs/
  architecture/
    README.md
    sprint-5-to-8-blueprint.md
    repository-target-structure.md
    gap-analysis-current-vs-target.md
  adr/
    0001-target-agentic-architecture.md

src/
  app.module.ts
  main.ts

  config/
    env.schema.ts
    settings.service.ts

  shared/
    domain/
      types/
      value-objects/
    application/
      ports/
    infrastructure/
      telemetry/
      logging/
      id/
    contracts/
      api/
      events/

  domains/
    knowledge/
      knowledge.module.ts
      application/
        dtos/
        use-cases/
      domain/
        interfaces/
        repositories/
        services/
      infrastructure/
        embeddings/
        indexing/
        loaders/
        parsers/
        persistence/
        ranking/
        retrieval/
      presentation/
        http/

    agent/
      agent.module.ts
      application/
        dtos/
        use-cases/
      domain/
        interfaces/
        repositories/
        services/
      infrastructure/
        guardrails/
        persistence/
        prompts/
        registry/
        tools/
      presentation/
        http/

    evaluation/
      evaluation.module.ts
      application/
        dtos/
        use-cases/
      domain/
        entities/
        interfaces/
        services/
      infrastructure/
        datasets/
        persistence/
        scorers/
        simulators/
      presentation/
        http/

    control/
      control.module.ts
      application/
        dtos/
        use-cases/
      domain/
        interfaces/
        services/
      infrastructure/
        analytics/
        dashboards/
        persistence/
      presentation/
        http/

    integrations/
      integrations.module.ts
      domain/
        interfaces/
      infrastructure/
        filesystem/
        http/
        mcp/
        python/
        sql/
        web/

workers/
  evaluator/
  indexer/
  cleanup/
```

## Arquivos concretos a criar por sprint

### Sprint 5

```text
src/domains/agent/domain/interfaces/agent-definition.interface.ts
src/domains/agent/domain/interfaces/agent-capability.interface.ts
src/domains/agent/domain/services/agent-registry.service.ts
src/domains/agent/domain/services/handoff-manager.service.ts
src/domains/agent/domain/services/conversation-memory.service.ts
src/domains/agent/domain/services/agent-orchestrator.service.ts
src/domains/agent/infrastructure/registry/default-agent-definitions.ts
src/domains/agent/infrastructure/tools/extract-structured-data.tool.ts
src/domains/agent/infrastructure/tools/get-document-by-id.tool.ts
src/domains/agent/infrastructure/tools/summarize-sources.tool.ts
```

### Sprint 6

```text
src/domains/evaluation/evaluation.module.ts
src/domains/evaluation/domain/entities/eval-case.entity.ts
src/domains/evaluation/domain/entities/eval-run.entity.ts
src/domains/evaluation/domain/services/eval-engine.service.ts
src/domains/evaluation/domain/services/critic-agent.service.ts
src/domains/evaluation/infrastructure/persistence/eval-run.schema.ts
src/domains/evaluation/infrastructure/persistence/eval-dataset.schema.ts
src/domains/evaluation/application/use-cases/run-eval-suite.use-case.ts
src/domains/evaluation/presentation/http/evaluation.controller.ts
src/domains/evaluation/infrastructure/datasets/core-regression.dataset.ts
```

### Sprint 7

```text
src/domains/control/control.module.ts
src/domains/control/domain/services/control-tower.service.ts
src/domains/control/domain/services/agent-analytics.service.ts
src/domains/control/application/use-cases/get-control-tower-snapshot.use-case.ts
src/domains/control/presentation/http/control.controller.ts
src/domains/control/infrastructure/persistence/tool-execution-audit.schema.ts
src/domains/control/infrastructure/persistence/agent-definition.schema.ts
src/domains/control/infrastructure/analytics/run-metrics.repository.ts
```

### Sprint 8

```text
src/domains/agent/application/dtos/ask-request.dto.ts
src/domains/agent/application/dtos/extract-request.dto.ts
src/domains/agent/application/dtos/act-request.dto.ts
src/domains/agent/application/use-cases/ask.use-case.ts
src/domains/agent/application/use-cases/extract.use-case.ts
src/domains/agent/application/use-cases/act.use-case.ts
src/domains/evaluation/infrastructure/simulators/run-simulation-harness.ts
docs/operations/agent-runtime-runbook.md
docs/operations/evaluation-runbook.md
```

## Mudancas concretas em arquivos ja existentes

### Sprint 5

- src/domains/agent/agent.module.ts
- src/domains/agent/domain/services/agent-loop.service.ts
- src/domains/agent/infrastructure/http/agent.controller.ts
- src/app.module.ts
- mongo-init-scripts/01-init-db.js

### Sprint 6

- src/app.module.ts
- mongo-init-scripts/01-init-db.js
- test/app.e2e-spec.ts

### Sprint 7

- src/app.module.ts
- mongo-init-scripts/01-init-db.js
- src/domains/agent/infrastructure/http/agent.controller.ts

### Sprint 8

- src/domains/agent/infrastructure/http/agent.controller.ts
- src/domains/evaluation/presentation/http/evaluation.controller.ts
- docs/operations/*.md

## Colecoes alvo do MongoDB

```text
knowledge_documents
knowledge_chunks
embeddings_index
conversations
prompt_templates
agent_runs
agent_steps
agent_memories
agent_definitions
tool_executions
eval_datasets
eval_runs
guardrail_events
feedback_events
search_logs
```

## Introducao incremental sem ruptura

### Fase 1

Adicionar novos dominios sem mover codigo antigo.

### Fase 2

Introduzir presentation/ gradualmente nos dominios novos e manter infrastructure/http/ nos dominios antigos.

### Fase 3

Convergir controllers antigos para presentation/http apenas quando os novos contratos estiverem estaveis.

## Regras de organizacao

- Use-cases continuam em application/use-cases.
- Contratos de repositorio continuam em domain/repositories.
- Services de orquestracao e policy ficam em domain/services.
- Schemas, repositorios concretos e ferramentas externas ficam em infrastructure.
- Controllers ficam em presentation/http para novos dominios.

## O que nao criar agora

- Microservicos separados por dominio.
- Mais de cinco agentes especializados.
- Filas externas obrigatorias.
- UI dedicada de observabilidade.

Esses itens devem vir apenas apos consolidacao do control plane e dos evals.
