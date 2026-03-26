---
agent: "NestJS Atlas Architect"
description: >
  Padroniza handoff entre equipes e especialistas do atlas_local com contexto,
  cenário, objetivo, restrições, evidências e critério de pronto.
---

## Contexto

Use este prompt quando uma análise, revisão ou diagnóstico precisar ser transferido
para outro especialista ou para outra equipe.

O agente que usa este prompt atua como **orquestrador do handoff**, não necessariamente como executor da próxima etapa.

## Template Obrigatório

```md
### Handoff
- Origem: [agente ou equipe que concluiu a etapa atual]
- Destino: [agente ou equipe responsável pela próxima etapa]
- Contexto: [qual problema está sendo resolvido]
- Cenário: [retrieval | llm | qa | testing | schema | arquitetura | infraestrutura | performance | cross-team]
- Objetivo: [resultado esperado]
- Restrições: [regras técnicas, compatibilidade, limites]
- Evidências: [métricas, docs, diagnósticos, benchmark, traces]
- Critério de pronto: [condições verificáveis para concluir]
```

## Checklist de Qualidade

1. O cenário principal foi explicitado?
2. O destino tem skill adequada para executar a próxima etapa?
3. Há evidência suficiente para agir sem recomeçar a análise?
4. O critério de pronto é verificável?
5. Há dependência de baseline, testes ou rollout local?

## Exemplos Concretos

### Exemplo 1 — Schema → Python/IA

```md
### Handoff
- Origem: Atlas Schema Expert
- Destino: Python IA Tech Lead
- Contexto: necessidade de modelar coleção para documentos indexados e chunks com evolução de schema
- Cenário: schema
- Objetivo: implementar persistência MongoDB com collections `knowledge_documents` e `knowledge_chunks`
- Restrições: seguir `snake_case` para collections, `camelCase` para campos, incluir `createdAt`, `updatedAt`, `schemaVersion`
- Evidências: design doc aprovado, queries frequentes por `sourceFile`, `chunkIndex` e busca textual
- Critério de pronto: collections criadas, índices nomeados explicitamente, testes de acesso passando
```

### Exemplo 2 — Infra → Python/IA

```md
### Handoff
- Origem: Atlas Local Infrastructure Expert
- Destino: Python IA Tech Lead
- Contexto: ambiente local precisa health checks e integração mais robusta com Atlas Local
- Cenário: infraestrutura
- Objetivo: ajustar bootstrap e conexão do app para validar MongoDB antes de inicializar serviços dependentes
- Restrições: usar `MONGODB_URI` via config central, preservar scripts em `scripts/windows/`, manter compatibilidade com Docker Compose atual
- Evidências: health check falhando intermitentemente, logs de startup incompletos, diagnóstico operacional documentado
- Critério de pronto: startup validado localmente, health check estável, testes relevantes passando
```

### Exemplo 3 — NestJS/Atlas → Python/IA para Retrieval

```md
### Handoff
- Origem: NestJS Atlas Architect
- Destino: Python IA Tech Lead
- Contexto: análise concluiu que o problema principal não é schema MongoDB e sim regressão no ranking híbrido
- Cenário: retrieval
- Objetivo: revisar fusão FTS5 + BM25 e validar impacto no baseline
- Restrições: comparar contra `data/eval_baseline.json`, manter explicabilidade do score, não introduzir vector search sem benchmark
- Evidências: queda de Top1, traces mostrando score opaco, queries metadata-heavy degradadas
- Critério de pronto: baseline revalidado, trace legível, testes de regressão adicionados
```

## Formato de Saída

```markdown
### Handoff Validado
[template preenchido]

### Lacunas
1. [item faltante]
2. [item faltante]

### Próxima Ação Recomendada
[o que o agente de destino deve executar primeiro]
```
