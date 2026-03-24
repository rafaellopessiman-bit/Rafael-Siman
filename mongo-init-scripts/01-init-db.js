// ── atlas_local — MongoDB Init Scripts ──────────────────────────────────────
// Executado automaticamente na primeira inicialização do container.
// Segue convenções: collections snake_case, campos camelCase,
// campos obrigatórios: createdAt, updatedAt, schemaVersion.
// ────────────────────────────────────────────────────────────────────────────

// Seleciona (e cria) o banco principal
const db = db.getSiblingDB("atlas_local_db");

// ── Criar usuário da aplicação (permissão mínima) ──────────────────────────
const appUser = process.env.MONGODB_APP_USER || "atlas_app";
const appPassword = process.env.MONGODB_APP_PASSWORD;
if (!appPassword) {
  print("⚠ MONGODB_APP_PASSWORD não definida — pulando criação do usuário da aplicação");
} else {
  db.createUser({
    user: appUser,
    pwd: appPassword,
    roles: [
      { role: "readWrite", db: "atlas_local_db" },
    ],
  });
  print("✔ Usuário " + appUser + " criado com permissão readWrite");
}

// ── Collections com validação de schema ────────────────────────────────────

// 1. knowledge_documents — documentos indexados para RAG
db.createCollection("knowledge_documents", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["sourceFile", "content", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        sourceFile: {
          bsonType: "string",
          description: "Caminho relativo do arquivo de origem",
        },
        content: {
          bsonType: "string",
          description: "Conteúdo textual do documento (ou chunk)",
        },
        chunkIndex: {
          bsonType: "int",
          minimum: 0,
          description: "Índice do chunk dentro do documento (0-based)",
        },
        fileType: {
          enum: [".txt", ".md", ".json", ".csv"],
          description: "Extensão do arquivo de origem",
        },
        charCount: {
          bsonType: "int",
          minimum: 0,
        },
        metadata: {
          bsonType: "object",
          description: "Metadados livres do documento",
        },
        isActive: {
          bsonType: "bool",
        },
        embedding: {
          bsonType: "array",
          items: { bsonType: "double" },
          description: "Vetor de embedding para busca vetorial (ex.: 1536-dim)",
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection knowledge_documents criada");

// Índices para knowledge_documents
db.knowledge_documents.createIndex(
  { sourceFile: 1, chunkIndex: 1 },
  { unique: true, name: "knowledge_documents_sourceFile_chunkIndex_unique_idx" }
);
db.knowledge_documents.createIndex(
  { content: "text" },
  { name: "knowledge_documents_content_text_idx", default_language: "portuguese" }
);
db.knowledge_documents.createIndex(
  { fileType: 1, isActive: 1 },
  { name: "knowledge_documents_fileType_isActive_idx" }
);

print("✔ Índices de knowledge_documents criados");

// 2. query_logs — log de queries e respostas do LLM
db.createCollection("query_logs", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["query", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        query: {
          bsonType: "string",
          description: "Pergunta do usuário",
        },
        response: {
          bsonType: "string",
          description: "Resposta gerada pelo LLM",
        },
        model: {
          bsonType: "string",
          description: "Modelo LLM utilizado",
        },
        sourcesUsed: {
          bsonType: "array",
          items: { bsonType: "string" },
          description: "Arquivos usados como contexto",
        },
        tokensUsed: {
          bsonType: "int",
          minimum: 0,
        },
        latencyMs: {
          bsonType: "int",
          minimum: 0,
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection query_logs criada");

// Índices para query_logs
db.query_logs.createIndex(
  { createdAt: -1 },
  { name: "query_logs_createdAt_idx" }
);
db.query_logs.createIndex(
  { model: 1, createdAt: -1 },
  { name: "query_logs_model_createdAt_idx" }
);

print("✔ Índices de query_logs criados");

// 3. llm_cache — cache de respostas do LLM (com TTL)
db.createCollection("llm_cache", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["queryHash", "response", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        queryHash: {
          bsonType: "string",
          description: "Hash SHA-256 da query + contexto",
        },
        response: {
          bsonType: "string",
        },
        model: {
          bsonType: "string",
        },
        hitCount: {
          bsonType: "int",
          minimum: 0,
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection llm_cache criada");

// Índices para llm_cache
db.llm_cache.createIndex(
  { queryHash: 1 },
  { unique: true, name: "llm_cache_queryHash_unique_idx" }
);
db.llm_cache.createIndex(
  { createdAt: 1 },
  { expireAfterSeconds: 86400, name: "llm_cache_createdAt_ttl_idx" }
);

print("✔ Índices de llm_cache criados");

// 4. document_index — índice de documentos processados
db.createCollection("document_index", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["sourceFile", "status", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        sourceFile: {
          bsonType: "string",
        },
        status: {
          enum: ["pending", "indexed", "failed", "archived"],
        },
        fileHash: {
          bsonType: "string",
          description: "SHA-256 do conteúdo para detecção de mudanças",
        },
        chunkCount: {
          bsonType: "int",
          minimum: 0,
        },
        totalChars: {
          bsonType: "int",
          minimum: 0,
        },
        lastIndexedAt: {
          bsonType: "date",
        },
        errorMessage: {
          bsonType: "string",
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection document_index criada");

// Índices para document_index
db.document_index.createIndex(
  { sourceFile: 1 },
  { unique: true, name: "document_index_sourceFile_unique_idx" }
);
db.document_index.createIndex(
  { status: 1, lastIndexedAt: -1 },
  { name: "document_index_status_lastIndexedAt_idx" }
);

print("✔ Índices de document_index criados");

// 5. conversations — histórico de conversas do agente IA
db.createCollection("conversations", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["title", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        title: {
          bsonType: "string",
          description: "Título da conversa",
        },
        systemPrompt: {
          bsonType: "string",
          description: "System prompt utilizado (literal ou slug de template)",
        },
        messages: {
          bsonType: "array",
          description: "Histórico de mensagens da conversa",
          items: {
            bsonType: "object",
            required: ["role", "timestamp"],
            properties: {
              role: {
                enum: ["system", "user", "assistant", "tool"],
              },
              content: {
                bsonType: ["string", "null"],
              },
              toolCallId: {
                bsonType: "string",
              },
              toolCalls: {
                bsonType: "array",
              },
              timestamp: {
                bsonType: "date",
              },
            },
          },
        },
        totalTokens: {
          bsonType: "int",
          minimum: 0,
        },
        messageCount: {
          bsonType: "int",
          minimum: 0,
        },
        isActive: {
          bsonType: "bool",
        },
        metadata: {
          bsonType: "object",
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection conversations criada");

// Índices para conversations
db.conversations.createIndex(
  { createdAt: -1 },
  { name: "conversations_createdAt_idx" }
);
db.conversations.createIndex(
  { isActive: 1, updatedAt: -1 },
  { name: "conversations_isActive_updatedAt_idx" }
);

print("✔ Índices de conversations criados");

// 6. prompt_templates — templates de system prompts configuráveis
db.createCollection("prompt_templates", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["slug", "name", "content", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        slug: {
          bsonType: "string",
          description: "Identificador único do template (ex: rag-default)",
        },
        name: {
          bsonType: "string",
          description: "Nome legível do template",
        },
        content: {
          bsonType: "string",
          description: "Conteúdo do system prompt",
        },
        description: {
          bsonType: "string",
        },
        isActive: {
          bsonType: "bool",
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection prompt_templates criada");

// Índices para prompt_templates
db.prompt_templates.createIndex(
  { slug: 1 },
  { unique: true, name: "prompt_templates_slug_unique_idx" }
);
db.prompt_templates.createIndex(
  { isActive: 1, name: 1 },
  { name: "prompt_templates_isActive_name_idx" }
);

print("✔ Índices de prompt_templates criados");

// 7. agent_runs — execuções (runs) do agente para tracing/observabilidade
db.createCollection("agent_runs", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["conversationId", "status", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        conversationId: {
          bsonType: "string",
          description: "ID da conversa associada",
        },
        status: {
          enum: ["running", "completed", "failed", "timeout"],
          description: "Estado atual do run",
        },
        triggeredBy: {
          bsonType: "string",
          description: "Quem iniciou o run (ex: api, scheduler)",
        },
        totalIterations: {
          bsonType: "int",
          minimum: 0,
        },
        totalTokens: {
          bsonType: "int",
          minimum: 0,
        },
        totalLatencyMs: {
          bsonType: "int",
          minimum: 0,
        },
        toolsUsed: {
          bsonType: "array",
          items: { bsonType: "string" },
        },
        finalAnswer: {
          bsonType: ["string", "null"],
        },
        errorMessage: {
          bsonType: ["string", "null"],
        },
        startedAt: {
          bsonType: "date",
        },
        finishedAt: {
          bsonType: ["date", "null"],
        },
        metadata: {
          bsonType: "object",
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection agent_runs criada");

db.agent_runs.createIndex(
  { conversationId: 1, createdAt: -1 },
  { name: "agent_runs_conversationId_createdAt_idx" }
);
db.agent_runs.createIndex(
  { status: 1, createdAt: -1 },
  { name: "agent_runs_status_createdAt_idx" }
);

print("✔ Índices de agent_runs criados");

// 8. agent_steps — steps atômicas dentro de cada run (tracing granular)
db.createCollection("agent_steps", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["runId", "stepNumber", "type", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        runId: {
          bsonType: "string",
          description: "ID do run associado",
        },
        stepNumber: {
          bsonType: "int",
          minimum: 1,
        },
        type: {
          enum: ["llm_call", "tool_call", "tool_result", "guardrail_input", "guardrail_output", "context_truncation", "final_answer"],
          description: "Tipo da step",
        },
        input: {
          bsonType: ["string", "null"],
        },
        output: {
          bsonType: ["string", "null"],
        },
        tokensUsed: {
          bsonType: "int",
          minimum: 0,
        },
        latencyMs: {
          bsonType: "int",
          minimum: 0,
        },
        toolName: {
          bsonType: ["string", "null"],
        },
        toolArgs: {
          bsonType: ["object", "null"],
        },
        metadata: {
          bsonType: "object",
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection agent_steps criada");

db.agent_steps.createIndex(
  { runId: 1, stepNumber: 1 },
  { name: "agent_steps_runId_stepNumber_idx" }
);

print("✔ Índices de agent_steps criados");

// 9. agent_definitions — definicoes versionadas de agentes especializados
db.createCollection("agent_definitions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id", "name", "description", "version", "systemPrompt", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        id: {
          bsonType: "string",
          description: "Identificador unico do agente (ex: knowledge_agent)",
        },
        name: {
          bsonType: "string",
          description: "Nome legivel do agente",
        },
        description: {
          bsonType: "string",
          description: "Descricao do proposito do agente",
        },
        version: {
          bsonType: "string",
          description: "Versao semântica da definicao",
        },
        capabilities: {
          bsonType: "array",
          items: {
            enum: ["KNOWLEDGE_RETRIEVAL", "STRUCTURED_EXTRACTION", "TOOL_EXECUTION", "CONTENT_CRITIQUE", "ORCHESTRATION"],
          },
          description: "Capacidades do agente",
        },
        allowedTools: {
          bsonType: "array",
          items: { bsonType: "string" },
          description: "Nomes das tools que o agente pode invocar",
        },
        handoffTargets: {
          bsonType: "array",
          items: { bsonType: "string" },
          description: "IDs dos agentes para os quais pode fazer handoff",
        },
        systemPrompt: {
          bsonType: "string",
          description: "System prompt do agente",
        },
        isActive: {
          bsonType: "bool",
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection agent_definitions criada");

db.agent_definitions.createIndex(
  { id: 1 },
  { unique: true, name: "agent_definitions_id_unique_idx" }
);
db.agent_definitions.createIndex(
  { isActive: 1 },
  { name: "agent_definitions_isActive_idx" }
);

print("✔ Índices de agent_definitions criados");

// 10. agent_memories — memorias resumidas de agentes por conversa
db.createCollection("agent_memories", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["conversationId", "agentId", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        conversationId: {
          bsonType: "string",
          description: "ID da conversa associada",
        },
        agentId: {
          bsonType: "string",
          description: "ID do agente que possui esta memoria",
        },
        summary: {
          bsonType: "string",
          description: "Resumo textual da conversa ate o momento",
        },
        keyFacts: {
          bsonType: "array",
          items: { bsonType: "string" },
          description: "Fatos-chave extraidos de runs anteriores",
        },
        runIds: {
          bsonType: "array",
          items: { bsonType: "string" },
          description: "IDs dos runs ja processados nesta memoria",
        },
        createdAt: {
          bsonType: "date",
        },
        updatedAt: {
          bsonType: "date",
        },
        schemaVersion: {
          bsonType: "int",
          minimum: 1,
        },
      },
    },
  },
});

print("✔ Collection agent_memories criada");

db.agent_memories.createIndex(
  { conversationId: 1, agentId: 1 },
  { unique: true, name: "agent_memories_conversationId_agentId_unique_idx" }
);
db.agent_memories.createIndex(
  { conversationId: 1 },
  { name: "agent_memories_conversationId_idx" }
);

print("✔ Índices de agent_memories criados");

// 11. eval_datasets — datasets de avaliação de qualidade (Sprint 6)
db.createCollection("eval_datasets", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id", "name", "version", "isRegression", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        id: { bsonType: "string", description: "ID único do dataset" },
        name: { bsonType: "string" },
        description: { bsonType: "string" },
        version: { bsonType: "string", description: "Versão semântica do dataset" },
        isRegression: { bsonType: "bool", description: "True = executado em CI automaticamente" },
        cases: {
          bsonType: "array",
          description: "Casos de avaliação contidos no dataset",
          items: {
            bsonType: "object",
            required: ["id", "datasetId", "input"],
            properties: {
              id: { bsonType: "string" },
              datasetId: { bsonType: "string" },
              input: { bsonType: "string" },
              expectedKeywords: { bsonType: "array", items: { bsonType: "string" } },
              forbiddenKeywords: { bsonType: "array", items: { bsonType: "string" } },
              expectedAgents: { bsonType: "array", items: { bsonType: "string" } },
              requiresCitations: { bsonType: "bool" },
              latencyBudgetMs: { bsonType: "int", minimum: 0 },
            },
          },
        },
        createdAt: { bsonType: "date" },
        updatedAt: { bsonType: "date" },
        schemaVersion: { bsonType: "int", minimum: 1 },
      },
    },
  },
});

print("✔ Collection eval_datasets criada");

db.eval_datasets.createIndex(
  { id: 1 },
  { unique: true, name: "eval_datasets_id_unique_idx" }
);
db.eval_datasets.createIndex(
  { isRegression: 1 },
  { name: "eval_datasets_isRegression_idx" }
);

print("✔ Índices de eval_datasets criados");

// 12. eval_runs — execuções de avaliação (Sprint 6)
db.createCollection("eval_runs", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id", "datasetId", "datasetVersion", "status", "startedAt", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        id: { bsonType: "string", description: "UUID do eval run" },
        datasetId: { bsonType: "string" },
        datasetVersion: { bsonType: "string" },
        status: { enum: ["pending", "running", "completed", "failed"] },
        triggeredBy: { bsonType: "string" },
        totalCases: { bsonType: "int", minimum: 0 },
        passedCases: { bsonType: "int", minimum: 0 },
        failedCases: { bsonType: "int", minimum: 0 },
        aggregateScore: {
          bsonType: "object",
          description: "Pontuação agregada do run por dimensão",
          properties: {
            faithfulness: { bsonType: ["double", "null"] },
            relevance: { bsonType: ["double", "null"] },
            completeness: { bsonType: ["double", "null"] },
            citationCoverage: { bsonType: ["double", "null"] },
            toolSuccess: { bsonType: ["double", "null"] },
            guardrailCompliance: { bsonType: ["double", "null"] },
            latencyBudget: { bsonType: ["double", "null"] },
            overallScore: { bsonType: "double" },
          },
        },
        startedAt: { bsonType: "date" },
        finishedAt: { bsonType: ["date", "null"] },
        durationMs: { bsonType: ["int", "null"] },
        createdAt: { bsonType: "date" },
        updatedAt: { bsonType: "date" },
        schemaVersion: { bsonType: "int", minimum: 1 },
      },
    },
  },
});

print("✔ Collection eval_runs criada");

db.eval_runs.createIndex(
  { id: 1 },
  { unique: true, name: "eval_runs_id_unique_idx" }
);
db.eval_runs.createIndex(
  { datasetId: 1, startedAt: -1 },
  { name: "eval_runs_datasetId_startedAt_idx" }
);
db.eval_runs.createIndex(
  { status: 1 },
  { name: "eval_runs_status_idx" }
);

print("✔ Índices de eval_runs criados");

// 13. tool_executions — trilha de auditoria de execução de tools (Sprint 7)
db.createCollection("tool_executions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["runId", "stepId", "agentId", "toolName", "status", "latencyMs", "executedAt", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        runId: { bsonType: "string" },
        stepId: { bsonType: "string" },
        agentId: { bsonType: "string" },
        toolName: { bsonType: "string" },
        toolArgs: { bsonType: ["object", "null"] },
        status: { enum: ["success", "error", "timeout", "blocked"] },
        result: { bsonType: ["string", "null"] },
        errorMessage: { bsonType: ["string", "null"] },
        latencyMs: { bsonType: "int", minimum: 0 },
        executedAt: { bsonType: "date" },
        createdAt: { bsonType: "date" },
        updatedAt: { bsonType: "date" },
        schemaVersion: { bsonType: "int", minimum: 1 },
      },
    },
  },
});

print("✔ Collection tool_executions criada");

db.tool_executions.createIndex(
  { runId: 1, executedAt: 1 },
  { name: "tool_executions_runId_executedAt_idx" }
);
db.tool_executions.createIndex(
  { agentId: 1, executedAt: -1 },
  { name: "tool_executions_agentId_executedAt_idx" }
);
db.tool_executions.createIndex(
  { toolName: 1, status: 1 },
  { name: "tool_executions_toolName_status_idx" }
);
db.tool_executions.createIndex(
  { executedAt: -1 },
  { name: "tool_executions_executedAt_idx" }
);

print("✔ Índices de tool_executions criados");

// 14. alert_rules — thresholds operacionais do control plane (Sprint 7)
db.createCollection("alert_rules", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["ruleId", "name", "metric", "operator", "threshold", "windowMinutes", "isActive", "createdAt", "updatedAt", "schemaVersion"],
      properties: {
        ruleId: { bsonType: "string" },
        name: { bsonType: "string" },
        metric: {
          enum: [
            "avg_latency_ms",
            "p95_latency_ms",
            "guardrail_block_rate",
            "error_rate",
            "tool_error_rate",
            "eval_overall_score"
          ]
        },
        operator: { enum: ["gt", "gte", "lt", "lte"] },
        threshold: { bsonType: ["int", "double"] },
        windowMinutes: { bsonType: "int", minimum: 1 },
        isActive: { bsonType: "bool" },
        createdAt: { bsonType: "date" },
        updatedAt: { bsonType: "date" },
        schemaVersion: { bsonType: "int", minimum: 1 },
      },
    },
  },
});

print("✔ Collection alert_rules criada");

db.alert_rules.createIndex(
  { ruleId: 1 },
  { unique: true, name: "alert_rules_ruleId_unique_idx" }
);
db.alert_rules.createIndex(
  { isActive: 1, metric: 1 },
  { name: "alert_rules_isActive_metric_idx" }
);

print("✔ Índices de alert_rules criados");

// ── Vector Search Index ────────────────────────────────────────────────────
// Criado apenas se o Atlas Local suportar $vectorSearch (atlas-local >= 7.0.6).
// O índice é idempotente — falha silenciosamente se já existir ou não suportado.
try {
  db.knowledge_documents.createSearchIndex({
    name: "knowledge_documents_embedding_vs_idx",
    type: "vectorSearch",
    definition: {
      fields: [
        {
          type: "vector",
          path: "embedding",
          numDimensions: 1536,
          similarity: "cosine",
        },
        {
          type: "filter",
          path: "fileType",
        },
        {
          type: "filter",
          path: "isActive",
        },
      ],
    },
  });
  print("✔ Vector Search index criado em knowledge_documents.embedding");
} catch (e) {
  print("⚠ Vector Search index não criado (requer Atlas Local >= 7.0.6): " + e.message);
}

print("");
print("═══════════════════════════════════════════════════");
print("  atlas_local_db inicializado com sucesso!");
print("  Collections: knowledge_documents, query_logs,");
print("               llm_cache, document_index,");
print("               conversations, prompt_templates,");
print("               agent_runs, agent_steps,");
print("               agent_definitions, agent_memories");
print("               eval_datasets, eval_runs,");
print("               tool_executions, alert_rules");
print("  Usuário app: atlas_app (readWrite)");
print("═══════════════════════════════════════════════════");
