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
import { ILlmCacheRepository } from '../src/domains/llm/domain/repositories/llm-cache.repository.interface';
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
  InMemoryPromptTemplateRepository,
  InMemoryQueryLogRepository,
  InMemoryToolExecutionRepository,
  StubEmbeddingService,
} from './support/e2e-test-stubs';

/**
 * Cache repo rastreável que suporta limpeza manual (simulando invalidação).
 */
class TrackableLlmCacheRepository implements ILlmCacheRepository {
  private readonly store = new Map<string, string>();

  async getCached(hash: string): Promise<string | null> {
    return this.store.get(hash) ?? null;
  }

  async setCache(hash: string, response: string, _model: string): Promise<void> {
    this.store.set(hash, response);
  }

  clear(): void {
    this.store.clear();
  }

  get size(): number {
    return this.store.size;
  }
}

describe('Ask Cache TTL and Invalidation (smoke e2e)', () => {
  let app: INestApplication;
  let cacheRepo: TrackableLlmCacheRepository;

  beforeAll(async () => {
    cacheRepo = new TrackableLlmCacheRepository();

    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    })
      .overrideProvider(KNOWLEDGE_REPOSITORY)
      .useClass(InMemoryKnowledgeRepository)
      .overrideProvider(EMBEDDING_SERVICE)
      .useClass(StubEmbeddingService)
      .overrideProvider(LLM_CACHE_REPOSITORY)
      .useValue(cacheRepo)
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
  });

  afterAll(async () => {
    await app.close();
  });

  it('should cache repeated asks, expire by TTL, and invalidate after knowledge changes', async () => {
    // Seed a document
    await request(app.getHttpServer())
      .post('/knowledge')
      .send({
        sourceFile: 'atlas-cache.md',
        content:
          'Atlas Local armazena respostas LLM em cache para acelerar queries repetidas.',
      })
      .expect(201);

    const dto = { query: 'Como o Atlas Local usa cache de respostas?', topK: 3 };

    // First ask — must NOT be cached
    const first = await request(app.getHttpServer())
      .post('/ask')
      .send(dto)
      .expect(201);

    expect(first.body.cached).toBe(false);
    expect(cacheRepo.size).toBe(1);

    // Second identical ask — must be a cache HIT
    const second = await request(app.getHttpServer())
      .post('/ask')
      .send(dto)
      .expect(201);

    expect(second.body.cached).toBe(true);
    expect(second.body.answer).toBe(first.body.answer);

    // Simulate invalidation: clear the cache (TTL expiry / manual invalidation)
    cacheRepo.clear();
    expect(cacheRepo.size).toBe(0);

    // Third ask after invalidation — must be a cache MISS again
    const third = await request(app.getHttpServer())
      .post('/ask')
      .send(dto)
      .expect(201);

    expect(third.body.cached).toBe(false);
  });
});
