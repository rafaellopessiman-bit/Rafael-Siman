# Atlas Local

## Sistema de inteligência documental

NestJS + MongoDB Atlas Local + Groq LLM

[![NestJS](https://img.shields.io/badge/NestJS-11-e0234e)](https://nestjs.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20Local-47A248)](https://www.mongodb.com/docs/atlas/cli/current/atlas-cli-deploy-local/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178c6)](https://www.typescriptlang.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Características

- **Indexação de Documentos** — Carrega TXT, MD, CSV, JSON, PDF, imagens OCR, DOCX e XLSX automaticamente
- **RAG com LLM** — Consultas respondidas com contexto (Groq / Llama 3.3 70B)
- **Planejamento Estruturado** — Gera planos detalhados com passos e riscos
- **Query em CSV** — SQL seguro em dados tabulares
- **MongoDB Atlas Local** — Schema validation, text search, TTL cache
- **Health Check** — Endpoint `/health` com Terminus + MongoDB ping
- **Swagger/OpenAPI** — Documentação automática em `/api`

---

## Stack

| Camada | Tecnologia |
| --- | --- |
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

- **API**: <http://localhost:3000>
- **Swagger**: <http://localhost:3000/api>
- **Health**: <http://localhost:3000/health>

---

## Estrutura do Projeto

```text
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
| --- | --- | --- |
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
DOCUMENTS_PATH=data/entrada
DATABASE_PATH=data/atlas_local.db
TOP_K=5
PDF_OCR_ENABLED=false
PDF_OCR_COMMAND=ocrmypdf
PDF_OCR_LANGUAGE=eng
IMAGE_OCR_ENABLED=false
IMAGE_OCR_COMMAND=tesseract
IMAGE_OCR_LANGUAGE=eng
SCHEDULE_EVAL_QUERIES_PATH=data/eval_queries.json
SCHEDULE_EVAL_BASELINE_PATH=data/eval_baseline.json
SCHEDULE_EVAL_TOP_K=5
SCHEDULE_NOTIFY_WEBHOOK_URL=
SCHEDULE_NOTIFY_TIMEOUT_SECONDS=10
SCHEDULE_NOTIFY_ON=on-issues
SCHEDULE_NOTIFY_FORMAT=raw
WATCH_INTERVAL_SECONDS=30
WATCH_REMEDIATION_POLICY=full-auto
REMEDIATION_ISOLATE_FLAGS=no_usable_chunks,very_short_document,repetitive_content,numeric_heavy,low_vocabulary_document
MONGODB_USER=admin
MONGODB_PASSWORD=AtlasLocal2026!Secure
MONGODB_PORT=27017
MONGODB_URI=mongodb://admin:AtlasLocal2026!Secure@localhost:27017/atlas_local_db?authSource=admin
MONGODB_DB=atlas_local_db
```

---

## Contrato de Embedding

| Propriedade | Valor | Onde está definido |
| --- | --- | --- |
| Modelo | `text-embedding-3-small` | `EMBEDDING_MODEL` no `.env` |
| Dimensão | 1536 | `EMBEDDING_DIMENSIONS` no `.env` + `numDimensions` em `01-init-db.js` |
| Similaridade | cosine | `01-init-db.js` (vectorSearch index) |
| Índice Atlas | `knowledge_documents_embedding_vs_idx` | `01-init-db.js` |

> **IMPORTANTE**: se a dimensão do embedding mudar, o índice vetorial em `mongo-init-scripts/01-init-db.js` **deve ser recriado**.

---

## Contrato de Chunking

| Parâmetro | Valor | Estratégia |
| --- | --- | --- |
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

### Indexação de biblioteca técnica

```bash
pip install -r requirements.txt
python -m src.main index --path "E:\\E-book" --db-path "data/ebooks_catalog.db" --workers 6 --batch-size 25
python -m src.main ask "Quais livros cobrem arquitetura, mongodb, rag e agentes?" --path "E:\\E-book" --db-path "data/ebooks_catalog.db"
```

### OCR seletivo para PDFs sem texto

- O OCR permanece desligado por padrao para nao encarecer a indexacao.
- Quando habilitado, o sistema tenta OCR apenas em PDFs sem texto extraivel.
- A integracao atual usa um comando externo configuravel, com default `ocrmypdf`.
- Imagens suportadas (`.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`) entram pela mesma logica, via OCR configuravel com default `tesseract`.
- Falhas recuperaveis entram na remediacao como `ocr_required`, em vez de serem tratadas como documento definitivamente ruim.

```bash
python -m src.main index --path "E:\\E-book" --db-path "data/ebooks_catalog.db" --enable-pdf-ocr --pdf-ocr-language "por+eng"
python -m src.main index --path "E:\\E-book" --db-path "data/ebooks_catalog.db" --enable-image-ocr --image-ocr-language "por"
python -m src.main audit --path "E:\\E-book" --db-path "data/ebooks_catalog.db" --enable-pdf-ocr --pdf-ocr-command "ocrmypdf" --pdf-ocr-language "por+eng" --output json
```

### Documentos Office

- `.docx` e `.xlsx` sao lidos diretamente sem dependencia obrigatoria extra, usando o conteudo OpenXML interno.
- Para `.xlsx`, o texto indexado inclui o nome da aba e as linhas com celulas extraiveis.

### OCR operacional em lote

- O `audit --output json` agora inclui `remediation.ocr_required_paths`.
- No Windows, use o script operacional abaixo para rodar OCR apenas nos PDFs sinalizados:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\ocr-flagged-pdfs.ps1 -AuditJsonPath .\audit.json -Language "por+eng"
```

### Política de remediação do corpus

- A variável `REMEDIATION_ISOLATE_FLAGS` controla quais flags isolam documentos durante `index` e `audit`.
- Flags fora dessa lista deixam de isolar e passam a gerar `index_with_review`, exceto duplicatas, que continuam em `ignore_duplicate`.
- O comportamento pode ser sobrescrito por comando com `--isolate-flags`.

```bash
python -m src.main audit --path "E:\\E-book" --db-path "data/ebooks_catalog.db" --isolate-flags "no_usable_chunks,repetitive_content"
python -m src.main index --path "E:\\E-book" --db-path "data/ebooks_catalog.db" --isolate-flags "numeric_heavy"
```

### Histórico de qualidade por documento

- O comando `history` consulta o histórico persistido no SQLite para um documento específico.
- É possível filtrar por origem do evento com `--source-command` e por ação de remediação com `--action`, incluindo `ocr_required`.

```bash
python -m src.main history "E:\\E-book\\doc.txt" --db-path "data/ebooks_catalog.db"
python -m src.main history "E:\\E-book\\doc.txt" --db-path "data/ebooks_catalog.db" --source-command audit --action index_with_review --output json
python -m src.main history "E:\\E-book\\scan.pdf" --db-path "data/ebooks_catalog.db" --action ocr_required --output json
```

O `audit` em JSON expoe `remediation.ocr_required_paths`, `review_paths`, `ignored_duplicate_paths` e `isolated_paths` para automacoes operacionais.

### Histórico operacional do schedule

- O comando `history-schedule` consulta diretamente no SQLite as execucoes persistidas do runner operacional.
- Ele suporta filtro por `status` e saida `text` ou `json`.

```bash
python -m src.main history-schedule --db-path "data/ebooks_catalog.db"
python -m src.main history-schedule --db-path "data/ebooks_catalog.db" --status partial --output json
```

### Relatório operacional

- O comando `report` consolida documentos indexados e a ultima decisao de auditoria/remediacao por arquivo.
- As saidas `json`, `csv`, `markdown` e `xlsx` usam a mesma base operacional.
- O modo `xlsx` gera abas operacionais como `Summary`, `LatestActions`, `PendingOCR`, `Review`, `Isolated`, `Duplicates` e `Documents`.
- A exportacao XLSX inclui cabecalho congelado, filtros automaticos e largura de coluna ajustada para leitura operacional.

```bash
python -m src.main report --db-path "data/ebooks_catalog.db" --output markdown
python -m src.main report --db-path "data/ebooks_catalog.db" --output json
python -m src.main report --db-path "data/ebooks_catalog.db" --output csv
python -m src.main report --db-path "data/ebooks_catalog.db" --output xlsx --output-path "data/processados/report.xlsx"
```

### Runner schedule

- O comando `schedule` executa `audit`, `report` e `ocr-pending` em sequencia, gerando artefatos operacionais em arquivo.
- Ele foi pensado para ser chamado por Task Scheduler, cron ou tarefas externas, sem exigir um daemon dedicado.
- Com `--reindex-after-ocr`, o runner reindexa automaticamente os artefatos OCR gerados para fechar o ciclo operacional na mesma execucao.
- O job `evaluate` pode ser executado dentro do schedule com comparacao automatica contra baseline.
- O runner sempre grava um `schedule-summary-*.json` consolidando status, passos e artefatos da execucao.
- Cada execucao do schedule tambem fica persistida no SQLite para historico operacional e tendencia recente.
- Opcionalmente, ele pode enviar esse payload para um webhook com `--notify-webhook-url` ou via configuracao `.env`, em formato `raw`, `teams` ou `slack`.
- Quando o `evaluate` detecta regressao critica em metricas agregadas, o schedule passa a devolver exit code diferente de zero.

```bash
python -m src.main schedule --path "E:\E-book" --db-path "data/ebooks_catalog.db" --output-dir "data/processados/schedule"
python -m src.main schedule --path "E:\E-book" --db-path "data/ebooks_catalog.db" --jobs audit report --report-output xlsx
python -m src.main schedule --path "E:\E-book" --db-path "data/ebooks_catalog.db" --jobs ocr-pending --ocr-in-place
python -m src.main schedule --path "E:\E-book" --db-path "data/ebooks_catalog.db" --jobs ocr-pending --ocr-in-place --reindex-after-ocr
python -m src.main schedule --path "E:\E-book" --db-path "data/ebooks_catalog.db" --jobs evaluate --eval-queries "data/eval_queries.json" --eval-baseline "data/eval_baseline.json"
python -m src.main schedule --path "E:\E-book" --db-path "data/ebooks_catalog.db" --jobs audit report evaluate --notify-webhook-url "https://localhost:8080/atlas" --notify-format teams --notify-on always
python -m src.main schedule --path "E:\E-book" --db-path "data/ebooks_catalog.db" --jobs evaluate --critical-regression-exit-code 7
```

No Windows, a rotina operacional recomendada fica em `scripts\windows\run-schedule-operational.ps1` e tambem pode ser executada pela task `Atlas: Schedule Operacional`.

- Para instalar a automacao no Task Scheduler do Windows 11, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-operational-tasks.ps1 -SourcePath "E:\E-book" -DatabasePath "data\ebooks_catalog.db"
```

- Para validar se o ambiente operacional do schedule esta pronto, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\health-check-operational.ps1 -SourcePath "E:\E-book" -DatabasePath "data\ebooks_catalog.db"
```

### Watch mode incremental

- O comando `watch` monitora a biblioteca local por polling e processa apenas arquivos novos, alterados ou removidos desde o ultimo ciclo.
- O snapshot do watch passa a ser persistido no SQLite, entao reinicios retomam do ultimo estado conhecido sem reprocessar todo o primeiro ciclo.
- A politica `ocr-required` faz uma segunda tentativa automatica com OCR quando um PDF ou imagem alterada falha inicialmente por falta de texto extraivel.
- A politica `full-auto` amplia isso com saneamento inicial de corpus e aplicacao repetivel das decisoes automaticas de isolamento e revisao com base nas regras ja existentes do audit.
- O historico gerado pelo watch tambem vai para o SQLite com `source_command=watch`, permitindo rastrear remediacao automatica no mesmo banco do corpus.

```bash
python -m src.main watch --path "E:\E-book" --db-path "data/ebooks_catalog.db"
python -m src.main watch --path "E:\E-book" --db-path "data/ebooks_catalog.db" --interval-seconds 15 --max-cycles 4
python -m src.main watch --path "E:\E-book" --db-path "data/ebooks_catalog.db" --remediation-policy manual
python -m src.main watch --path "E:\E-book" --db-path "data/ebooks_catalog.db" --remediation-policy ocr-required --pdf-ocr-command ocrmypdf --image-ocr-command tesseract
python -m src.main watch --path "E:\E-book" --db-path "data/ebooks_catalog.db" --remediation-policy full-auto --isolate-flags "no_usable_chunks,repetitive_content"
```

No Windows, a rotina operacional recomendada fica em `scripts\windows\run-watch-operational.ps1` e pode ser executada pela task `Atlas: Watch Operacional`.

- A instalacao automatica no Task Scheduler cria duas tarefas idempotentes: `Atlas Local - Watch Operacional` e `Atlas Local - Schedule Operacional`.
- O health-check operacional verifica Python, scripts, paths, OCR local, disponibilidade dos comandos `watch` e `schedule`, Task Scheduler e as tasks registradas.

O pipeline de PDF extrai texto interno com `pypdf`, infere metadados heurísticos e indexa um catálogo pesquisável por tema, autor, stack e conceitos. Veja [docs/PDF_INDEXING_PIPELINE.md](docs/PDF_INDEXING_PIPELINE.md).

---

## Licença

MIT
