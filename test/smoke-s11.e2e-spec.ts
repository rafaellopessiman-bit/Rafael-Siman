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

describe('Sprint 11 — Persistent Queue + Observability (smoke e2e)', () => {
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

  // ── S11: Default driver = event_emitter (backward compat) ───────────────
  describe('POST /knowledge/async (default driver)', () => {
    it('should return 202 with driver=event_emitter by default', async () => {
      const res = await request(app.getHttpServer())
        .post('/knowledge/async')
        .send({
          sourceFile: 's11-test.md',
          content: 'Sprint 11 driver test content.',
        })
        .expect(202);

      expect(res.body).toHaveProperty('jobId');
      expect(res.body).toHaveProperty('status', 'accepted');
      expect(res.body).toHaveProperty('driver', 'event_emitter');
      expect(typeof res.body.jobId).toBe('string');
    });

    it('should still reject invalid payload (missing sourceFile)', async () => {
      await request(app.getHttpServer())
        .post('/knowledge/async')
        .send({ content: 'No sourceFile.' })
        .expect(400);
    });

    it('should still reject empty content', async () => {
      await request(app.getHttpServer())
        .post('/knowledge/async')
        .send({ sourceFile: 'test.md', content: '' })
        .expect(400);
    });
  });

  // ── S11: Correlation ID still works ─────────────────────────────────────
  describe('Correlation ID on async endpoint', () => {
    it('should propagate x-correlation-id on POST /knowledge/async', async () => {
      const customId = 's11-corr-id-test';
      const res = await request(app.getHttpServer())
        .post('/knowledge/async')
        .set('x-correlation-id', customId)
        .send({
          sourceFile: 'corr-test.md',
          content: 'Correlation test.',
        })
        .expect(202);

      expect(res.headers['x-correlation-id']).toBe(customId);
    });
  });

  // ── S11: Config vars loaded ─────────────────────────────────────────────
  describe('Config (Zod validated)', () => {
    it('app should boot with new Redis/driver/cache config defaults', () => {
      // If we got here, the app booted successfully with the new
      // Zod schema entries (REDIS_HOST, REDIS_PORT, INDEX_ASYNC_DRIVER, etc.)
      expect(app).toBeDefined();
    });
  });

  // ── S11: BullMQ not registered when driver=event_emitter ────────────────
  describe('BullMQ isolation', () => {
    it('should not have /knowledge/jobs route when driver=event_emitter', async () => {
      const res = await request(app.getHttpServer())
        .get('/knowledge/jobs/nonexistent-job');

      // Route should not exist — 404 from router, not from controller
      expect(res.status).toBe(404);
    });
  });
});
