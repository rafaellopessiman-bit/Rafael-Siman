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
import {
  TOOL_EXECUTION_REPOSITORY,
  IToolExecutionRepository,
} from '../src/domains/control/domain/repositories/tool-execution.repository.interface';
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

describe('Act Surface (smoke e2e)', () => {
  let app: INestApplication;
  let toolExecutionRepository: IToolExecutionRepository;

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

    toolExecutionRepository = moduleFixture.get(TOOL_EXECUTION_REPOSITORY);
    app = moduleFixture.createNestApplication();
    applyTestAppConfig(app);
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  it('should execute a governed action and persist an audit trail', async () => {
    const response = await request(app.getHttpServer())
      .post('/act')
      .send({
        intent: 'refresh sources index',
        allowedActions: ['refresh_sources_index'],
        contextId: 'conv-123',
      })
      .expect(201);

    expect(response.body).toHaveProperty('toolName', 'execute_whitelisted_action');
    expect(response.body).toHaveProperty('action', 'refresh_sources_index');
    expect(response.body).toHaveProperty('mode', 'live');
    expect(response.body).toHaveProperty('status', 'success');
    expect(response.body).toHaveProperty('audited', true);
    expect(response.body).toHaveProperty('resultData.mode', 'live');
    expect(response.body.resultData).toHaveProperty('details');

    const recentExecutions = await toolExecutionRepository.findRecent(1);
    expect(recentExecutions).toHaveLength(1);
    expect(recentExecutions[0]).toHaveProperty('toolName', 'execute_whitelisted_action');
    expect(recentExecutions[0]).toHaveProperty('agentId', 'tool_agent');
  });

  it('should reject unsupported allowedActions before execution', async () => {
    await request(app.getHttpServer())
      .post('/act')
      .send({
        intent: 'delete production data',
        allowedActions: ['drop_everything'],
      })
      .expect(400);
  });

  it('should sync control metrics with real aggregation', async () => {
    const response = await request(app.getHttpServer())
      .post('/act')
      .send({
        intent: 'sync control metrics',
        allowedActions: ['sync_control_metrics'],
      })
      .expect(201);

    expect(response.body).toHaveProperty('mode', 'live');
    expect(response.body).toHaveProperty('status', 'success');
    expect(response.body.resultData).toHaveProperty('details.period', '24h');
    expect(response.body.resultData.details).toHaveProperty('totalExecutions');
  });

  it('should execute preview external lookup with real knowledge search', async () => {
    const response = await request(app.getHttpServer())
      .post('/act')
      .send({
        intent: 'preview external lookup for pricing data',
        allowedActions: ['preview_external_lookup'],
      })
      .expect(201);

    expect(response.body).toHaveProperty('mode', 'live');
    expect(response.body).toHaveProperty('status', 'success');
    expect(response.body.resultData).toHaveProperty('details.query');
    expect(response.body.resultData.details).toHaveProperty('resultCount');
  });
});