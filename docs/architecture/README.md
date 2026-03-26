# Atlas Local Architecture Pack

Este diretorio consolida a arquitetura-alvo do atlas_local e o plano de evolucao a partir do estado atual.

## Conteudo

1. [sprint-traceability-map-1-to-13.md](./sprint-traceability-map-1-to-13.md)
   Mapa canonico de rastreabilidade dos Sprints 1 a 13, separando evidencia explicita de documentacao retrospectiva.

2. [retrospective-sprints-1-to-4-foundation.md](./retrospective-sprints-1-to-4-foundation.md)
   Documentacao retrospectiva padronizada da fundacao legada do produto antes da fase agentic.

3. [retrospective-sprint-9-security-hardening.md](./retrospective-sprint-9-security-hardening.md)
   Documentacao retrospectiva padronizada da camada de seguranca e controle de acesso.

4. [sprint-5-to-8-blueprint.md](./sprint-5-to-8-blueprint.md)
   Blueprint tecnico do Sprint 5 ao Sprint 8, com ordem exata de implementacao.

5. [repository-target-structure.md](./repository-target-structure.md)
   Estrutura concreta de pastas e arquivos a criar no repositorio, com fases de introducao.

6. [gap-analysis-current-vs-target.md](./gap-analysis-current-vs-target.md)
   Comparacao entre o estado atual do atlas_local e a arquitetura-alvo, gap por gap.

7. [../adr/0001-target-agentic-architecture.md](../adr/0001-target-agentic-architecture.md)
   ADR formalizando a arquitetura-alvo da plataforma.

## Principios desta arquitetura

- Monolito modular primeiro, sem migracao prematura para microservicos.
- Knowledge plane forte como nucleo do produto.
- Agent runtime com supervisor, handoffs, memoria, guardrails e tool execution governada.
- Control plane explicito para tracing, evals, observabilidade e governanca.
- Evolucao incremental por sprint, com validacao por testes e datasets de avaliacao.

## Produtos de referencia usados como inspiracao

- Glean Agents
- Amazon Bedrock Agents
- Kore.ai Agent Platform
- Intercom Fin
- Moveworks
- ServiceNow AI Agents

## Escopo assumido

- Volume inicial pequeno de documentos.
- Concorrencia baixa no horizonte de 12 meses.
- Produto hibrido: knowledge engine privado + runtime agentic.
- Casos de uso principais: perguntas sobre documentos, busca semantica, extracao estruturada, tools e multiagente.
