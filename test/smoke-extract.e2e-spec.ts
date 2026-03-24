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

describe('Extract Surface (smoke e2e)', () => {
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
  });

  afterAll(async () => {
    await app.close();
  });

  it('should extract structured data using an explicit output schema', async () => {
    await request(app.getHttpServer())
      .post('/knowledge')
      .send({
        sourceFile: 'contrato-atlas.md',
        content: 'Empresa: Atlas Local. Status: ativo. Ambiente: homologacao.',
      })
      .expect(201);

    const response = await request(app.getHttpServer())
      .post('/extract')
      .send({
        query: 'Extraia empresa e status do contrato',
        outputSchema: {
          type: 'object',
          properties: {
            empresa: { type: 'string' },
            status: { type: 'string' },
          },
          required: ['empresa', 'status'],
        },
        sourceIds: ['contrato-atlas.md'],
      })
      .expect(201);

    expect(response.body).toHaveProperty('validJson', true);
    expect(response.body).toHaveProperty('schemaValid', true);
    expect(response.body).toHaveProperty('validationErrors');
    expect(response.body.validationErrors).toEqual([]);
    expect(response.body).toHaveProperty('data.empresa', 'Atlas Local');
    expect(response.body).toHaveProperty('data.status', 'ativo');
    expect(response.body.sources).toContain('contrato-atlas.md');
  });

  it('should validate enum constraints in outputSchema', async () => {
    await request(app.getHttpServer())
      .post('/knowledge')
      .send({
        sourceFile: 'enum-test.md',
        content: 'Empresa: Atlas Local. Status: ativo.',
      })
      .expect(201);

    const response = await request(app.getHttpServer())
      .post('/extract')
      .send({
        query: 'Extraia empresa e status',
        outputSchema: {
          type: 'object',
          properties: {
            empresa: { type: 'string' },
            status: { type: 'string', enum: ['ativo', 'inativo', 'pendente'] },
          },
          required: ['empresa', 'status'],
        },
        sourceIds: ['enum-test.md'],
      })
      .expect(201);

    expect(response.body).toHaveProperty('validJson', true);
    expect(response.body).toHaveProperty('schemaValid', true);
    expect(response.body.validationErrors).toEqual([]);
  });

  it('should detect enum violations in extracted data', async () => {
    await request(app.getHttpServer())
      .post('/knowledge')
      .send({
        sourceFile: 'enum-violation.md',
        content: 'Empresa: Atlas Local. Status: ativo.',
      })
      .expect(201);

    const response = await request(app.getHttpServer())
      .post('/extract')
      .send({
        query: 'Extraia empresa e status',
        outputSchema: {
          type: 'object',
          properties: {
            empresa: { type: 'string' },
            status: { type: 'string', enum: ['cancelado', 'expirado'] },
          },
          required: ['empresa', 'status'],
        },
        sourceIds: ['enum-violation.md'],
      })
      .expect(201);

    expect(response.body).toHaveProperty('validJson', true);
    // The stub returns status: 'ativo' which is not in ['cancelado', 'expirado']
    expect(response.body).toHaveProperty('schemaValid', false);
    expect(response.body.validationErrors.length).toBeGreaterThan(0);
  });
});