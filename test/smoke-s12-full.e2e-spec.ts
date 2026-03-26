import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../src/app.module';
import { KNOWLEDGE_REPOSITORY } from '../src/domains/knowledge/domain/repositories/knowledge.repository.interface';
import { EMBEDDING_SERVICE } from '../src/domains/knowledge/domain/services/embedding.service';
import { LLM_CACHE_REPOSITORY } from '../src/domains/llm/domain/repositories/llm-cache.repository.interface';
import { QUERY_LOG_REPOSITORY } from '../src/domains/llm/domain/repositories/query-log.repository.interface';
import { DOCUMENT_INDEX_REPOSITORY } from '../src/domains/planner/domain/repositories/document-index.repository.interface';
import { CONVERSATION_REPOSITORY } from '../src/domains/agent/domain/repositories/conversation.repository.interface';
import { PROMPT_TEMPLATE_REPOSITORY } from '../src/domains/agent/domain/repositories/prompt-template.repository.interface';
import { AGENT_RUN_REPOSITORY } from '../src/domains/agent/domain/repositories/agent-run.repository.interface';
import { AGENT_STEP_REPOSITORY } from '../src/domains/agent/domain/repositories/agent-step.repository.interface';
import { AGENT_DEFINITION_REPOSITORY } from '../src/domains/agent/domain/repositories/agent-definition.repository.interface';
import { AGENT_MEMORY_REPOSITORY } from '../src/domains/agent/domain/repositories/agent-memory.repository.interface';
import { EVAL_DATASET_REPOSITORY } from '../src/domains/evaluation/domain/repositories/eval-dataset.repository.interface';
import { EVAL_RUN_REPOSITORY } from '../src/domains/evaluation/domain/repositories/eval-run.repository.interface';
import { TOOL_EXECUTION_REPOSITORY } from '../src/domains/control/domain/repositories/tool-execution.repository.interface';
import { ALERT_RULE_REPOSITORY } from '../src/domains/control/domain/repositories/alert-rule.repository.interface';
import { GroqClientService } from '../src/domains/llm/infrastructure/groq/groq-client.service';
import {
  applyTestAppConfig,
  ConditionalGroqClientService,
  InMemoryAgentDefinitionRepository,
  InMemoryAgentMemoryRepository,
  InMemoryAgentRunRepository,
  InMemoryAgentStepRepository,
  InMemoryAlertRuleRepository,
  InMemoryConversationRepository,
  InMemoryDocumentIndexRepository,
  InMemoryEvalDatasetRepository,
  InMemoryEvalRunRepository,
  InMemoryKnowledgeRepository,
  InMemoryLlmCacheRepository,
  InMemoryPromptTemplateRepository,
  InMemoryQueryLogRepository,
  InMemoryToolExecutionRepository,
  StubEmbeddingService,
} from './support/e2e-test-stubs';

jest.setTimeout(60000);

describe('Sprint 12 — Cache, Pagination, Upload, Scheduler (e2e)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    })
      .overrideProvider(KNOWLEDGE_REPOSITORY)
      .useClass(InMemoryKnowledgeRepository)
      .overrideProvider(EMBEDDING_SERVICE)
      .useClass(StubEmbeddingService)
      .overrideProvider(LLM_CACHE_REPOSITORY)
      .useClass(InMemoryLlmCacheRepository)
      .overrideProvider(QUERY_LOG_REPOSITORY)
      .useClass(InMemoryQueryLogRepository)
      .overrideProvider(DOCUMENT_INDEX_REPOSITORY)
      .useClass(InMemoryDocumentIndexRepository)
      .overrideProvider(CONVERSATION_REPOSITORY)
      .useClass(InMemoryConversationRepository)
      .overrideProvider(PROMPT_TEMPLATE_REPOSITORY)
      .useClass(InMemoryPromptTemplateRepository)
      .overrideProvider(AGENT_RUN_REPOSITORY)
      .useClass(InMemoryAgentRunRepository)
      .overrideProvider(AGENT_STEP_REPOSITORY)
      .useClass(InMemoryAgentStepRepository)
      .overrideProvider(AGENT_DEFINITION_REPOSITORY)
      .useClass(InMemoryAgentDefinitionRepository)
      .overrideProvider(AGENT_MEMORY_REPOSITORY)
      .useClass(InMemoryAgentMemoryRepository)
      .overrideProvider(EVAL_DATASET_REPOSITORY)
      .useClass(InMemoryEvalDatasetRepository)
      .overrideProvider(EVAL_RUN_REPOSITORY)
      .useClass(InMemoryEvalRunRepository)
      .overrideProvider(TOOL_EXECUTION_REPOSITORY)
      .useClass(InMemoryToolExecutionRepository)
      .overrideProvider(ALERT_RULE_REPOSITORY)
      .useClass(InMemoryAlertRuleRepository)
      .overrideProvider(GroqClientService)
      .useClass(ConditionalGroqClientService)
      .compile();

    app = moduleFixture.createNestApplication();
    applyTestAppConfig(app);
    await app.init();
  }, 60000);

  afterAll(async () => {
    await app.close();
  });

  // ── Pagination ─────────────────────────────────────────────────────

  describe('GET /knowledge (pagination)', () => {
    it('should return paginated response with meta', async () => {
      const res = await request(app.getHttpServer())
        .get('/knowledge?page=1&limit=10')
        .expect(200);

      expect(res.body).toHaveProperty('data');
      expect(res.body).toHaveProperty('meta');
      expect(res.body.meta).toEqual(
        expect.objectContaining({
          page: 1,
          limit: 10,
          total: expect.any(Number),
          totalPages: expect.any(Number),
        }),
      );
      expect(Array.isArray(res.body.data)).toBe(true);
    });

    it('should default to page=1 limit=20 when no params', async () => {
      const res = await request(app.getHttpServer())
        .get('/knowledge')
        .expect(200);

      expect(res.body.meta.page).toBe(1);
      expect(res.body.meta.limit).toBe(20);
    });

    it('should reject limit > 100', async () => {
      await request(app.getHttpServer())
        .get('/knowledge?limit=200')
        .expect(400);
    });
  });

  // ── File Upload ────────────────────────────────────────────────────

  describe('POST /knowledge/upload', () => {
    it('should upload a .txt file and index it', async () => {
      const res = await request(app.getHttpServer())
        .post('/knowledge/upload')
        .attach('file', Buffer.from('Conteúdo de teste para indexação'), {
          filename: 'test-upload.txt',
          contentType: 'text/plain',
        })
        .expect(201);

      expect(res.body).toEqual(
        expect.objectContaining({
          sourceFile: 'test-upload.txt',
          fileType: '.txt',
          sizeBytes: expect.any(Number),
          chunksCreated: expect.any(Number),
        }),
      );
    });

    it('should upload a .md file', async () => {
      const res = await request(app.getHttpServer())
        .post('/knowledge/upload')
        .attach('file', Buffer.from('# Título\n\nConteúdo markdown'), {
          filename: 'readme.md',
          contentType: 'text/markdown',
        })
        .expect(201);

      expect(res.body.fileType).toBe('.md');
    });

    it('should upload a .json file', async () => {
      const res = await request(app.getHttpServer())
        .post('/knowledge/upload')
        .attach('file', Buffer.from(JSON.stringify({ chave: 'valor' })), {
          filename: 'data.json',
          contentType: 'application/json',
        })
        .expect(201);

      expect(res.body.fileType).toBe('.json');
    });

    it('should upload a .csv file', async () => {
      const res = await request(app.getHttpServer())
        .post('/knowledge/upload')
        .attach('file', Buffer.from('nome,idade\nJoão,30'), {
          filename: 'dados.csv',
          contentType: 'text/csv',
        })
        .expect(201);

      expect(res.body.fileType).toBe('.csv');
    });

    it('should reject forbidden extension (.exe)', async () => {
      await request(app.getHttpServer())
        .post('/knowledge/upload')
        .attach('file', Buffer.from('malicious content'), {
          filename: 'virus.exe',
          contentType: 'application/octet-stream',
        })
        .expect(400);
    });

    it('should appear in paginated listing after upload', async () => {
      const res = await request(app.getHttpServer())
        .get('/knowledge?page=1&limit=50')
        .expect(200);

      expect(res.body.meta.total).toBeGreaterThan(0);
      expect(res.body.data.length).toBeGreaterThan(0);
    });
  });

  // ── Cache Integration ──────────────────────────────────────────────

  describe('Cache metrics via /metrics', () => {
    it('should record cache miss on first ask', async () => {
      await request(app.getHttpServer())
        .post('/llm/ask')
        .send({ query: 'O que é o atlas local?' })
        .expect(201);

      const metrics = await request(app.getHttpServer())
        .get('/metrics')
        .expect(200);

      expect(metrics.text).toContain('atlas_ask_cache_total');
    });

    it('should record cache hit on repeated ask', async () => {
      // First call
      await request(app.getHttpServer())
        .post('/llm/ask')
        .send({ query: 'Cache integration test query' })
        .expect(201);

      // Second call (same query — should hit cache)
      const result = await request(app.getHttpServer())
        .post('/llm/ask')
        .send({ query: 'Cache integration test query' })
        .expect(201);

      expect(result.body.cached).toBe(true);
    });
  });

  // ── Upload Metrics ─────────────────────────────────────────────────

  describe('Upload metrics', () => {
    it('should record upload success metric', async () => {
      await request(app.getHttpServer())
        .post('/knowledge/upload')
        .attach('file', Buffer.from('Metrics test content'), {
          filename: 'metrics-test.txt',
          contentType: 'text/plain',
        })
        .expect(201);

      const metrics = await request(app.getHttpServer())
        .get('/metrics')
        .expect(200);

      expect(metrics.text).toContain('atlas_knowledge_uploads_total');
    });
  });

  // ── Scheduler presence ─────────────────────────────────────────────

  describe('Scheduler module', () => {
    it('should boot without errors (scheduler registered)', async () => {
      // If ScheduleModule failed to load, app.init() above would throw.
      // Simple sanity: app is running.
      const res = await request(app.getHttpServer())
        .get('/health')
        .expect(200);

      expect(res.body.status).toBeDefined();
    });
  });
});
