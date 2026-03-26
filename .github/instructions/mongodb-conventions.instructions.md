---
description: >
  Use when: writing MongoDB schemas, collections, documents, indexes, aggregation pipelines,
  data models, ODM classes, or any code that interacts with MongoDB Atlas Local.
  Covers naming conventions, field design, index definitions, and document structure rules.
applyTo: src/**
---

# MongoDB Conventions — atlas_local

## Nomenclatura

| Elemento | Convenção | Exemplo |
|---|---|---|
| Collection name | `snake_case`, plural | `knowledge_documents`, `user_sessions` |
| Campo de documento | `camelCase` | `createdAt`, `sourceFile`, `chunkIndex` |
| Campo `_id` | `ObjectId` padrão do MongoDB (nunca renomear) | `_id` |
| Índice | `<collection>_<campos>_idx` | `knowledge_documents_sourceFile_createdAt_idx` |
| Database name | `snake_case` | `atlas_local_dev`, `atlas_local_test` |
| Variáveis Python | `snake_case` conforme PEP 8 | `document_store`, `chunk_index` |

## Campos Obrigatórios em Todo Documento

Todo documento deve conter:

```python
{
    "_id":       ObjectId(),          # gerado automaticamente
    "createdAt": datetime.utcnow(),   # sempre UTC
    "updatedAt": datetime.utcnow(),   # atualizar em todo upsert
    "schemaVersion": 1,               # incrementar ao mudar estrutura
}
```

## Regras de Design de Campos

- **Nunca armazene arrays ilimitados** em um único documento — use referenciação quando o array pode crescer além de ~100 elementos.
- **Prefira embedding** quando os dados são sempre lidos juntos e a sub-entidade tem ciclo de vida dependente do pai.
- **Use referenciação** quando a sub-entidade é compartilhada entre documentos ou pode ser consultada de forma independente.
- **Datas**: sempre `datetime` UTC — nunca strings ISO sem timezone.
- **Booleanos**: prefixo `is` ou `has` (`isActive`, `hasAttachment`).
- **Enums**: armazene como `string` em lowercase (`"active"`, `"archived"`), nunca como inteiro.

## Índices

Defina índices no arquivo de inicialização do banco (ex.: `src/storage/document_store.py`):

```python
# Índice composto: campo mais seletivo primeiro
collection.create_index([("sourceFile", ASCENDING), ("createdAt", DESCENDING)], name="knowledge_documents_sourceFile_createdAt_idx")

# Índice de texto para busca full-text
collection.create_index([("content", TEXT)], name="knowledge_documents_content_text_idx")

# TTL para expiração automática (ex.: cache)
collection.create_index("createdAt", expireAfterSeconds=86400, name="cache_createdAt_ttl_idx")
```

**Regras:**

- Todo índice deve ter `name` explícito.
- Nunca crie índice em campo de cardinalidade baixa (ex.: `isActive` booleano) de forma isolada.
- Revise com `explain()` antes de declarar produção.

## Conexão — Atlas Local

```python
# URI padrão para Atlas Local em desenvolvimento
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME     = os.getenv("MONGODB_DB",  "atlas_local_dev")
```

Nunca hardcode a URI. Sempre via variável de ambiente com fallback para `localhost:27017`.

## Anti-padrões Proibidos

- `db["MyCollection"]` — use sempre `snake_case`.
- Armazenar JSON serializado como `string` dentro de um campo.
- Documento com mais de ~16 MB (limite hard do MongoDB).
- `update_many` sem filtro restritivo em produção.
- Ignorar `schemaVersion` ao mudar a estrutura de um documento existente.
