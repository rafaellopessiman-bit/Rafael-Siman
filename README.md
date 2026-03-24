# Atlas Local

**Sistema de inteligência documental — NestJS + MongoDB Atlas Local + Groq LLM**

[![NestJS](https://img.shields.io/badge/NestJS-11-e0234e)](https://nestjs.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20Local-47A248)](https://www.mongodb.com/docs/atlas/cli/current/atlas-cli-deploy-local/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178c6)](https://www.typescriptlang.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Características

- **Indexação de Documentos** — Carrega TXT, MD, CSV e JSON automaticamente
- **RAG com LLM** — Consultas respondidas com contexto (Groq / Llama 3.3 70B)
- **Planejamento Estruturado** — Gera planos detalhados com passos e riscos
- **Query em CSV** — SQL seguro em dados tabulares
- **MongoDB Atlas Local** — Schema validation, text search, TTL cache
- **Health Check** — Endpoint `/health` com Terminus + MongoDB ping
- **Swagger/OpenAPI** — Documentação automática em `/api`

---

## Stack

| Camada | Tecnologia |
|---|---|
| Framework | NestJS 11 (TypeScript strict) |
| Banco de dados | MongoDB Atlas Local (Docker) |
| ODM | Mongoose 8 + @nestjs/mongoose |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Validação | Zod (env) + class-validator (DTOs) |
| Testes | Jest + Supertest |
| Docs | @nestjs/swagger (OpenAPI 3) |

---

## Quick Start

### 1. Pré-requisitos

- Docker + Docker Compose
- Node.js 22 LTS (ou use o Dev Container)

### 2. Setup

```bash
# Copiar variáveis de ambiente
cp .env.example .env
# Editar .env com sua GROQ_API_KEY

# Subir MongoDB + NestJS
docker compose up -d

# Ou abrir no VS Code Dev Container (recomendado)
# Ctrl+Shift+P → "Reabrir no Contêiner"
```

### 3. Instalar dependências (sem Docker)

```bash
npm ci
npm run start:dev
```

### 4. Acessar

- **API**: http://localhost:3000
- **Swagger**: http://localhost:3000/api
- **Health**: http://localhost:3000/health

---

## Estrutura do Projeto

```
src/
  main.ts                    # Bootstrap NestJS
  app.module.ts              # Root module
  config/                    # ConfigModule + Zod env validation
  database/                  # MongooseModule connection factory
  health/                    # HealthModule (Terminus + MongoDB ping)
  domains/
    knowledge/               # KnowledgeModule (chunking + embedding + text/vector search)
    llm/                     # LLM Module (Groq client + cache + query logs)
    planner/                 # PlannerModule (document index tracking)
    tabular/                 # TabularModule (SQL validation)
    shared/                  # Enums compartilhados (DocumentStatus, FileType)
  shared/                    # Filters, Interceptors
tests/                       # Testes Python (pytest, 81 testes)
mongo-init-scripts/          # Schema validation + índices (auto-executed)
test/                        # E2E tests (Jest + Supertest)
data/
  entrada/                   # Documentos para indexação
  indice/                    # Índice gerado
  processados/               # Artefatos processados
docs/                        # Documentação do projeto
_archive/                    # Backups e scripts históricos
```

---

## MongoDB Collections

| Collection | Descrição | Índices |
|---|---|---|
| `knowledge_documents` | Documentos indexados para RAG | sourceFile+chunkIndex unique, content text, embedding vectorSearch, fileType+isActive |
| `query_logs` | Log de queries e respostas LLM | createdAt, model+createdAt |
| `llm_cache` | Cache de respostas (TTL 24h) | queryHash unique, createdAt TTL |
| `document_index` | Tracking de documentos processados | sourceFile unique, status+lastIndexedAt |

---

## Variáveis de Ambiente

```env
NODE_ENV=development
APP_PORT=3000
GROQ_API_KEY=sua-chave-aqui
GROQ_MODEL=llama-3.3-70b-versatile
MONGODB_USER=admin
MONGODB_PASSWORD=AtlasLocal2026!Secure
MONGODB_PORT=27017
MONGODB_URI=mongodb://admin:AtlasLocal2026!Secure@localhost:27017/atlas_local_db?authSource=admin
MONGODB_DB=atlas_local_db
```

---

## Contrato de Embedding

| Propriedade | Valor | Onde está definido |
|---|---|---|
| Modelo | `text-embedding-3-small` | `EMBEDDING_MODEL` no `.env` |
| Dimensão | 1536 | `EMBEDDING_DIMENSIONS` no `.env` + `numDimensions` em `01-init-db.js` |
| Similaridade | cosine | `01-init-db.js` (vectorSearch index) |
| Índice Atlas | `knowledge_documents_embedding_vs_idx` | `01-init-db.js` |

> **IMPORTANTE**: se a dimensão do embedding mudar, o índice vetorial em `mongo-init-scripts/01-init-db.js` **deve ser recriado**.

---

## Contrato de Chunking

| Parâmetro | Valor | Estratégia |
|---|---|---|
| `maxChars` | 1000 | Tamanho máximo por chunk |
| `overlap` | 120 | Sobreposição entre chunks adjacentes |
| `.md` | Segmentação por headings | Cada seção `#` vira segmento |
| `.json` | Flatten + window | Chaves achatadas, depois janeladas |
| `.txt` / `.csv` | Parágrafos | Separação por `\n\n` |

O chunking é aplicado automaticamente no `POST /knowledge` quando `chunkIndex` não é fornecido.

---

## Testes

```bash
# Unit tests
npm test

# E2E tests
npm run test:e2e

# Com cobertura
npm run test:cov
```

---

## Python CLI

O código Python coexiste em `src/` junto com o TypeScript. Os testes estão em `tests/`:

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m src.main --help
python -m pytest tests/ -v
```

---

## Licença

MIT
