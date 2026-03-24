# Runbook Operacional do Runtime Agentic

## Objetivo

Este runbook cobre a operacao diaria das surfaces Ask, Extract e Act, alem do runtime multiagente do atlas_local.

## Superficies ativas

- POST /ask: RAG com grounding e citacoes
- POST /extract: extracao estruturada guiada por JSON Schema
- POST /act: execucao governada de tools com audit trail em tool_executions
- POST /agent/conversations/:id/orchestrate: fluxo multiagente supervisor + especialistas

## Pre-check de subida

1. Confirmar ambiente Python e Node instalados
2. Confirmar MongoDB Atlas Local em execucao
3. Confirmar variaveis do .env

```powershell
.\scripts\windows\health-check.ps1
```

## Startup recomendado

```powershell
.\scripts\windows\start-all.ps1
```

## Verificacoes operacionais

### 1. Saude geral da stack

```powershell
.\scripts\windows\health-check.ps1
```

### 2. Verificar surfaces HTTP

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:3000/ask -ContentType application/json -Body '{"query":"Explique o Atlas Local","topK":3}'
Invoke-RestMethod -Method Post -Uri http://localhost:3000/extract -ContentType application/json -Body '{"query":"Extraia empresa e status","outputSchema":{"type":"object","properties":{"empresa":{"type":"string"},"status":{"type":"string"}},"required":["empresa","status"]}}'
Invoke-RestMethod -Method Post -Uri http://localhost:3000/act -ContentType application/json -Body '{"intent":"refresh sources index","allowedActions":["refresh_sources_index"]}'
```

### 3. Verificar audit trail operacional

- GET /control/dashboard para metricas agregadas
- GET /control/health para alertas ativos
- Confirmar crescimento de tool_executions apos chamadas em /act

## Falhas comuns e resposta

### Ask sem grounding

- Sintoma: response com grounded=false e sem citations
- Verificar: indexacao da base em data/entrada e /knowledge
- Acao: reindexar documentos

```powershell
.\scripts\windows\reindex-docs.ps1
```

### Extract com validJson=false

- Sintoma: payload retorna data.rawResult
- Verificar: outputSchema malformado ou contexto insuficiente
- Acao: reduzir escopo via sourceIds e simplificar o schema

### Act rejeitada

- Sintoma: erro de governanca ou action nao suportada
- Verificar: allowedActions do request e whitelist do tool_agent
- Acao: usar uma das acoes suportadas: refresh_sources_index, sync_control_metrics, preview_external_lookup

## Observabilidade

- Agent runs: GET /agent/runs
- Steps por run: GET /agent/runs/:runId/steps
- Dashboard: GET /control/dashboard
- Alertas: GET /control/health

## Rollback rapido

1. Parar stack
2. Restaurar backup
3. Subir stack novamente

```powershell
.\scripts\windows\stop-all.ps1
.\scripts\windows\restore-mongo.ps1
.\scripts\windows\start-all.ps1
```

## Validacao antes de deploy local

```powershell
npx tsc --noEmit
npm run test:e2e
```
