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
import { ConfigService } from '@nestjs/config';
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

/**
 * ConfigService stub que força ATLAS_VECTOR_SEARCH_ENABLED=true.
 * Necessário porque forRoot() lê process.env sincronamente na decoração
 * do módulo, antes de qualquer beforeAll.
 */
class VectorEnabledConfigService {
  get<T = unknown>(key: string, defaultValue?: T): T | undefined {
    if (key === 'ATLAS_VECTOR_SEARCH_ENABLED') return 'true' as unknown as T;
    if (key === 'THROTTLE_TTL') return 60000 as unknown as T;
    if (key === 'THROTTLE_LIMIT') return 30 as unknown as T;
    const envVal = process.env[key as string];
    return (envVal !== undefined ? envVal : defaultValue) as T | undefined;
  }
  getOrThrow<T = unknown>(key: string): T {
    const v = this.get<T>(key);
    if (v === undefined) throw new TypeError(`Configuration key "${key}" does not exist`);
    return v as T;
  }
}

/**
 * Knowledge repo stub que rastreia chamadas a vectorSearch.
 * Permite verificar que o caminho de vector search foi exercitado.
 */
class SpyKnowledgeRepository extends InMemoryKnowledgeRepository {
  vectorSearchCalls = 0;
  textSearchCalls = 0;

  override async vectorSearch(embedding: number[], limit: number) {
    this.vectorSearchCalls++;
    return super.vectorSearch(embedding, limit);
  }

  override async searchText(query: string, limit: number) {
    this.textSearchCalls++;
    return super.searchText(query, limit);
  }
}

describe('Vector Search Ask Path (smoke e2e)', () => {
  let app: INestApplication;
  let knowledgeRepo: SpyKnowledgeRepository;

  beforeAll(async () => {
    knowledgeRepo = new SpyKnowledgeRepository();

    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    })
      .overrideProvider(KNOWLEDGE_REPOSITORY)
      .useValue(knowledgeRepo)
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
      .overrideProvider(ConfigService)
      .useValue(new VectorEnabledConfigService())
      .compile();

    app = moduleFixture.createNestApplication();
    applyTestAppConfig(app);
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  it('should use vectorSearch instead of text search when the vector flag is enabled', async () => {
    // Seed a document via knowledge endpoint
    await request(app.getHttpServer())
      .post('/knowledge')
      .send({
        sourceFile: 'atlas-vector.md',
        content: 'Atlas Local usa busca vetorial com embeddings de 1536 dimensões.',
      })
      .expect(201);

    expect(knowledgeRepo.vectorSearchCalls).toBe(0);

    // Execute ask — should route through vectorSearch path
    const response = await request(app.getHttpServer())
      .post('/ask')
      .send({
        query: 'Como o Atlas Local realiza busca?',
        topK: 3,
      })
      .expect(201);

    expect(response.body).toHaveProperty('answer');
    expect(typeof response.body.answer).toBe('string');

    // textSearch must NOT have been called; vectorSearch MUST have been called
    expect(knowledgeRepo.textSearchCalls).toBe(0);
    expect(knowledgeRepo.vectorSearchCalls).toBeGreaterThanOrEqual(1);
  });
});
