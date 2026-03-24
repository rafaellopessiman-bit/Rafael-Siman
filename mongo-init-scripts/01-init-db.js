// ── atlas_local — MongoDB Init Scripts ──────────────────────────────────────
// Executado automaticamente na primeira inicialização do container.
// Segue convenções: collections snake_case, campos camelCase,
// campos obrigatórios: createdAt, updatedAt, schemaVersion.
// ────────────────────────────────────────────────────────────────────────────

// Seleciona (e cria) o banco principal
const db = db.getSiblingDB("atlas_local_db");

// ── Criar usuário da aplicação (permissão mínima) ──────────────────────────
db.createUser({
  user: "atlas_app",
  pwd: "AtlasApp2026!Secure",
  roles: [
    { role: "readWrite", db: "atlas_local_db" },
  ],
});

print("✔ Usuário atlas_app criado com permissão readWrite");

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

print("");
print("═══════════════════════════════════════════════════");
print("  atlas_local_db inicializado com sucesso!");
print("  Collections: knowledge_documents, query_logs,");
print("               llm_cache, document_index");
print("  Usuário app: atlas_app (readWrite)");
print("═══════════════════════════════════════════════════");
