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

describe('Sprint 12 — Metrics endpoint (smoke e2e)', () => {
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

  it('should expose Prometheus metrics without API key', async () => {
    const res = await request(app.getHttpServer()).get('/metrics').expect(200);

    expect(res.headers['content-type']).toContain('text/plain');
    expect(res.text).toContain('atlas_http_request_duration_ms');
    expect(res.text).toContain('atlas_knowledge_queue_jobs_total');
  });

  it('should record HTTP metrics after a regular request', async () => {
    await request(app.getHttpServer()).get('/health').expect(200);

    const res = await request(app.getHttpServer()).get('/metrics').expect(200);

    expect(res.text).toContain('method="GET"');
    expect(res.text).toContain('route="/health"');
    expect(res.text).toContain('status="200"');
  });
});
