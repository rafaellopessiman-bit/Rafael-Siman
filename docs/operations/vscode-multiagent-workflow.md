# Fluxo Multiagente no VS Code

## Objetivo

Este playbook adapta o material que ja existe no repositorio para um fluxo multiagente previsivel no VS Code: triagem, execucao especializada, handoff e validacao.

## Artefatos Reaproveitados

- Agentes: `.github/agents/*.agent.md`
- Prompts: `.github/prompts/*.prompt.md`
- Instrucoes compartilhadas: `.github/copilot-instructions.md`
- Validacoes locais: `.vscode/tasks.json`

## Fluxo Recomendado

### 1. Triagem

Comece com `.github/prompts/initial-triage.prompt.md`.

Resultado esperado:

- cenario principal definido
- equipe responsavel definida
- especialista primario definido
- decisao explicita sobre handoff

### 2. Lideranca da Demanda

Use apenas um lider por vez:

- `NestJS Atlas Architect`
  - schema
  - arquitetura
  - infraestrutura
  - performance MongoDB
- `Python IA Tech Lead`
  - implementacao Python
  - retrieval
  - LLM
  - testing
  - QA

### 3. Especialista Primario

Depois da triagem, escolha um especialista dono da execucao.

Evite paralelismo artificial. Abra um segundo especialista apenas quando houver escopo independente, por exemplo:

- schema + infraestrutura
- retrieval + testing
- implementacao + QA final

### 4. Handoff Estruturado

Quando a tarefa mudar de dono, use `.github/prompts/cross-team-handoff.prompt.md`.

O handoff deve carregar:

- contexto
- cenario
- objetivo
- restricoes
- evidencias
- criterio de pronto

### 5. Fechamento e Gate

No final, rode as validacoes locais apropriadas.

Tasks recomendadas:

- `Atlas: Multiagent - Preflight`
- `Python: Executar Testes`
- `Atlas: Type Check`
- `NestJS: Executar Testes e2e`
- `Atlas: Multiagent - Gate Completo`

## Roteiros Prontos

### Nova feature Python

1. Triagem com `initial-triage`
2. Lider: `Python IA Tech Lead`
3. Especialista primario: `Python Testing Specialist` primeiro, depois implementacao
4. Revisao final: `Python QA Reviewer`
5. Gate: `Atlas: Multiagent - Gate Completo`

### Regressao de retrieval

1. Triagem com `initial-triage`
2. Lider: `Python IA Tech Lead`
3. Especialista primario: `Python Retrieval Architect`
4. Exigir baseline/evaluate antes e depois
5. Revisao final com `Python QA Reviewer`

### Problema de schema ou Atlas Local

1. Triagem com `initial-triage`
2. Lider: `NestJS Atlas Architect`
3. Especialista primario: `Atlas Schema Expert`, `Atlas Architect` ou `Atlas Local Infrastructure Expert`
4. Se virar implementacao Python, emitir handoff para `Python IA Tech Lead`
5. Validar com tasks do workspace conforme a mudanca

## Prompt de Entrada Unificado

Para iniciar a orquestracao sem montar o fluxo manualmente, use `.github/prompts/multiagent-delivery.prompt.md`.

Esse prompt foi criado para:

- classificar a demanda
- escolher o lider
- limitar a fragmentacao
- explicitar handoffs
- fechar com gate de validacao
