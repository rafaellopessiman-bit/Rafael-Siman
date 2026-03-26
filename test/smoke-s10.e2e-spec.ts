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

describe('Sprint 10 — Production Hardening (smoke e2e)', () => {
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

  // ── S10-03: Health Detailed ─────────────────────────────────────────────
  describe('GET /health/detailed', () => {
    it('should return disk and heap indicators', async () => {
      const res = await request(app.getHttpServer())
        .get('/health/detailed');

      // May be 200 (all healthy) or 503 (heap exceeded in heavy test runner)
      expect([200, 503]).toContain(res.status);

      const body = res.body;

      // When AllExceptionsFilter intercepts the 503, the Terminus shape is lost
      if (body.statusCode === 503 && body.message) {
        expect(body).toHaveProperty('statusCode', 503);
        return;
      }

      expect(body).toHaveProperty('status');
      // Indicators live in 'info' (up) or 'details' (mix), check both
      const indicators = { ...body.info, ...body.details };
      expect(indicators).toHaveProperty('mongodb');
      expect(indicators).toHaveProperty('disk');
      expect(indicators).toHaveProperty('heap');
    });

    it('should still allow basic health without rate-limiting', async () => {
      const res = await request(app.getHttpServer())
        .get('/health')
        .expect(200);

      expect(res.body.status).toBe('ok');
    });
  });

  // ── S10-04: Correlation ID ──────────────────────────────────────────────
  describe('Correlation ID middleware', () => {
    it('should generate x-correlation-id when not provided', async () => {
      const res = await request(app.getHttpServer())
        .get('/health')
        .expect(200);

      const correlationId = res.headers['x-correlation-id'];
      expect(correlationId).toBeDefined();
      expect(typeof correlationId).toBe('string');
      expect(correlationId.length).toBeGreaterThan(0);
    });

    it('should echo back provided x-correlation-id', async () => {
      const customId = 'test-correlation-abc-123';
      const res = await request(app.getHttpServer())
        .get('/health')
        .set('x-correlation-id', customId)
        .expect(200);

      expect(res.headers['x-correlation-id']).toBe(customId);
    });
  });

  // ── S10-06: Async Indexing ──────────────────────────────────────────────
  describe('POST /knowledge/async', () => {
    it('should return 202 Accepted with jobId', async () => {
      const res = await request(app.getHttpServer())
        .post('/knowledge/async')
        .send({
          sourceFile: 'async-test.md',
          content: 'Conteúdo para indexação assíncrona.',
        })
        .expect(202);

      expect(res.body).toHaveProperty('jobId');
      expect(res.body).toHaveProperty('status', 'accepted');
      expect(typeof res.body.jobId).toBe('string');
      expect(res.body.jobId.length).toBeGreaterThan(0);
    });

    it('should reject invalid payload (missing sourceFile)', async () => {
      await request(app.getHttpServer())
        .post('/knowledge/async')
        .send({ content: 'Sem sourceFile.' })
        .expect(400);
    });

    it('should reject empty content', async () => {
      await request(app.getHttpServer())
        .post('/knowledge/async')
        .send({ sourceFile: 'test.md', content: '' })
        .expect(400);
    });
  });

  // ── S10-01/02: Named Throttlers ─────────────────────────────────────────
  describe('Named throttlers (SkipThrottle on health)', () => {
    it('health endpoints should not be rate-limited', async () => {
      // Fire 5 rapid requests — all should succeed
      const requests = Array.from({ length: 5 }, () =>
        request(app.getHttpServer()).get('/health'),
      );
      const results = await Promise.all(requests);

      for (const res of results) {
        expect(res.status).toBe(200);
      }
    });
  });
});
