# Runbook de Avaliacao Continua

## Objetivo

Este runbook descreve como validar continuamente a qualidade das surfaces Ask, Extract e Act usando suites smoke e os endpoints do dominio evaluation.

## Suites obrigatorias

- test/smoke-ask.e2e-spec.ts
- test/smoke-extract.e2e-spec.ts
- test/smoke-act.e2e-spec.ts
- test/evaluation.e2e-spec.ts

## Execucao local recomendada

```powershell
npm run test:e2e
```

## Validacao dirigida por endpoint

### 1. Rodar avaliacoes persistidas

- POST /eval/run
- GET /eval/runs
- GET /eval/runs/:id
- GET /eval/runs/dataset/:datasetId

### 2. Interpretar o resultado

- faithfulness: grounding da resposta
- relevance: aderencia ao pedido do usuario
- completeness: cobertura dos requisitos
- citationCoverage: presenca de citacoes quando exigidas
- toolSuccess: execucao bem-sucedida das tools
- guardrailCompliance: ausencia de bloqueios indevidos
- latencyBudget: aderencia ao budget operacional

## Procedimento de regressao

1. Rodar TypeScript check
2. Rodar e2e completo
3. Inspecionar novas falhas nas smoke suites
4. Confirmar que /control/health nao degrada apos o teste

```powershell
npx tsc --noEmit
npm run test:e2e
```

## Criticos para investigar imediatamente

- citationCoverage abaixo do esperado
- regressao em /ask sem citations
- /extract retornando validJson=false com schema simples
- /act sem registro correspondente em tool_executions
- aumento abrupto de p95 latency no dashboard

## Evidencias minimas para aprovar mudanca

- TypeScript sem erros
- Todas as suites e2e verdes
- Pelo menos uma execucao auditada em /act observavel no control dashboard
- Nenhum alerta critico inesperado em /control/health

## Quando atualizar o dataset

- Nova capability de tool
- Mudanca de prompt default de agentes
- Mudanca no formato de citacao
- Mudanca em thresholds de guardrail

## Rotina semanal recomendada

1. Rodar npm run test:e2e
2. Revisar resultados recentes em /eval/runs
3. Revisar /control/dashboard para latencia, error rate e guardrail blocks
4. Reindexar documentos se houve alteracao relevante da base
