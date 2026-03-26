---
agent: "NestJS Atlas Architect"
description: >
  Orquestra uma demanda ponta a ponta no atlas_local usando os agentes ja definidos:
  triagem, escolha do lider, execucao especializada, handoff e gate final de validacao.
---

## Contexto

Use este prompt para conduzir uma demanda no atlas_local de forma parecida com um fluxo multiagente do VS Code, sem criar over-orchestration.

O objetivo e reaproveitar os artefatos ja existentes:

- `initial-triage.prompt.md` para classificar o pedido
- `cross-team-handoff.prompt.md` para transferencias entre especialistas ou equipes
- `.github/agents/*.agent.md` para escolher o papel correto
- `.vscode/tasks.json` para validar o resultado localmente

## Sequencia Obrigatoria

1. Fazer uma triagem inicial do pedido e escolher um **cenario principal**
2. Definir um **lider responsavel**:
   - NestJS Atlas Architect para schema, arquitetura, infraestrutura e performance MongoDB
   - Python IA Tech Lead para implementacao Python, retrieval, LLM, testes e QA
3. Escolher **um especialista primario**
4. Acionar especialista de apoio apenas se houver ganho real de especializacao ou escopo claramente separado
5. Se houver troca entre equipes, emitir handoff completo
6. Ao fim, encaminhar o gate de validacao apropriado
7. Consolidar resultado, riscos residuais e proxima acao

## Regras de Orquestracao

- Nao fragmente tarefas simples em varios especialistas
- Nao pule a triagem inicial
- Nao faca handoff sem contexto, evidencias e criterio de pronto
- Para mudancas em retrieval, ranking ou scoring, exigir baseline/evaluate antes e depois
- Para feature nova em Python, priorizar workflow TDD com o Python Testing Specialist
- Para mudancas em schema, Docker, Atlas Local ou arquitetura, manter a equipe NestJS/Atlas como dona da analise
- Para revisar mudanca pronta, encaminhar ao Python QA Reviewer antes de encerrar

## Gate de Validacao do Workspace

Use as tasks abaixo no fechamento da demanda:

- `Atlas: Multiagent - Preflight`
- `Python: Executar Testes`
- `Atlas: Type Check`
- `NestJS: Executar Testes e2e`
- `Atlas: Multiagent - Gate Completo`

## Formato de Saida

```md
### Execucao Multiagente
- Pedido resumido: [1 frase]
- Cenario principal: [retrieval | llm | qa | testing | schema | arquitetura | infraestrutura | performance]
- Lider responsavel: [NestJS Atlas Architect | Python IA Tech Lead]
- Especialista primario: [nome do agente]
- Especialista(s) de apoio: [opcional]
- Precisa handoff?: [sim/nao]

### Plano de Execucao
1. [passo com responsavel]
2. [passo com responsavel]
3. [passo com responsavel]

### Handoff
[preencher somente se houver troca de especialista ou equipe]

### Gate de Validacao
- Task recomendada: [nome da task]
- Evidencia esperada: [teste, baseline, type check, e2e, runbook]

### Encerramento
- Resultado esperado: [o que deve ficar pronto]
- Riscos residuais: [lista curta]
- Proxima acao: [passo seguinte claro]
```
