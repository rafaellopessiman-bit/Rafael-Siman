import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import { getModelToken } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import * as request from 'supertest';
import { randomUUID } from 'crypto';
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
import { AllExceptionsFilter } from '../src/shared/filters/all-exceptions.filter';
import { LoggingInterceptor } from '../src/shared/interceptors/logging.interceptor';
import { AgentRun, AgentRunDocument } from '../src/domains/agent/infrastructure/persistence/agent-run.schema';

class InMemoryKnowledgeRepository {
  async create(d: Record<string, unknown>) { return { ...d, _id: randomUUID(), charCount: 0, isActive: true, createdAt: new Date(), updatedAt: new Date(), schemaVersion: 1 }; }
  async findBySourceFile() { return []; }
  async searchText(_q: string, _limit: number) { return []; }
  async vectorSearch(_e: number[], _limit: number) { return []; }
  async deleteBySourceFile() { return 0; }
}

class StubEmbeddingService {
  readonly model = 'stub';
  readonly dimensions = 1536;
  async embed() { return new Array(1536).fill(0); }
  async embedBatch(texts: string[]) { return texts.map(() => new Array(1536).fill(0)); }
}

class InMemoryLlmCacheRepository {
  async getCached() { return null; }
  async setCache() {}
}

class InMemoryQueryLogRepository {
  async logQuery() {}
}

class InMemoryDocumentIndexRepository {
  async upsertIndex(sourceFile: string, data: Record<string, unknown>) {
    return { sourceFile, ...data, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() };
  }
  async findPending() { return []; }
  async findAll() { return []; }
}

class StubGroqClientService {
  get isConfigured() { return false; }
  async chatCompletion() { return { content: '[stub]', tokensUsed: 42, model: 'stub' }; }
  async chatCompletionWithTools() { return { content: '[agent stub]', tokensUsed: 50, model: 'stub', toolCalls: undefined }; }
}

class InMemoryConversationRepository {
  async create(data: Record<string, unknown>) { return { _id: 'conv-1', ...data, messages: [], totalTokens: 0, messageCount: 0, isActive: true, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() }; }
  async findById() { return null; }
  async findAll() { return []; }
  async appendMessage() { return null; }
  async addTokens() {}
  async archive() {}
}

class InMemoryPromptTemplateRepository {
  async create(data: Record<string, unknown>) { return { ...data, isActive: true, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() }; }
  async findBySlug() { return null; }
  async findAll() { return []; }
  async update() { return null; }
  async deactivate() {}
}

class InMemoryAgentRunRepository {
  async create(data: Record<string, unknown>) { return { _id: randomUUID(), ...data, totalIterations: 0, totalTokens: 0, totalLatencyMs: 0, toolsUsed: [], startedAt: new Date(), schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() }; }
  async finalize() { return null; }
  async findById() { return null; }
  async findByConversation() { return []; }
  async findRecent() { return []; }
}

class InMemoryAgentStepRepository {
  async create(data: Record<string, unknown>) { return { ...data, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() }; }
  async findByRun() { return []; }
}

class InMemoryAgentDefinitionRepository {
  private defs = [
    {
      id: 'supervisor_agent',
      name: 'Supervisor',
      description: 'Supervisor default',
      version: '1.0.0',
      capabilities: ['orchestration'],
      allowedTools: [],
      handoffTargets: [],
      systemPrompt: 'stub',
      isActive: true,
    },
  ];

  async findById(id: string) { return this.defs.find((d) => d.id === id) ?? null; }
  async findAll() { return [...this.defs]; }
  async findActive() { return this.defs.filter((d) => d.isActive); }
  async upsert(definition: Record<string, unknown>) {
    const idx = this.defs.findIndex((d) => d.id === definition['id']);
    const doc = definition as typeof this.defs[number];
    if (idx >= 0) { this.defs[idx] = doc; } else { this.defs.push(doc); }
    return doc;
  }
}

class InMemoryAgentMemoryRepository {
  async findByConversationAndAgent() { return null; }
  async upsert(data: Record<string, unknown>) { return { ...data, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() }; }
  async findRecent() { return []; }
}

class InMemoryEvalDatasetRepository {
  async findById() { return null; }
  async findAll() { return []; }
  async findRegression() { return []; }
  async upsert(dataset: Record<string, unknown>) { return dataset; }
}

class InMemoryEvalRunRepository {
  private runs: Array<Record<string, unknown>> = [];

  async create(run: Record<string, unknown>) {
    const doc = { ...run, schemaVersion: 1 };
    this.runs.push(doc);
    return doc;
  }

  async findById(id: string) {
    return this.runs.find((r) => r['id'] === id) ?? null;
  }

  async findByDataset(datasetId: string, limit = 20) {
    return this.runs.filter((r) => r['datasetId'] === datasetId).slice(0, limit);
  }

  async findRecent(limit = 10) {
    return [...this.runs].reverse().slice(0, limit);
  }

  async update(id: string, data: Record<string, unknown>) {
    const idx = this.runs.findIndex((r) => r['id'] === id);
    if (idx < 0) return null;
    this.runs[idx] = { ...this.runs[idx], ...data };
    return this.runs[idx];
  }

  seed(run: Record<string, unknown>) {
    this.runs.push(run);
  }
}

class InMemoryToolExecutionRepository {
  private executions: Array<Record<string, unknown>> = [];

  async create(data: Record<string, unknown>) {
    const doc = { id: randomUUID(), ...data, schemaVersion: 1 };
    this.executions.push(doc);
    return doc;
  }

  async findByRun(runId: string) {
    return this.executions.filter((e) => e['runId'] === runId);
  }

  async findByAgent(agentId: string, limit = 50) {
    return this.executions.filter((e) => e['agentId'] === agentId).slice(0, limit);
  }

  async findRecent(limit = 50) {
    return [...this.executions].reverse().slice(0, limit);
  }

  async countByStatusSince(since: Date) {
    const counts: Record<string, number> = {};
    for (const execution of this.executions) {
      const executedAt = execution['executedAt'] as Date;
      if (executedAt < since) continue;
      const status = execution['status'] as string;
      counts[status] = (counts[status] ?? 0) + 1;
    }
    return counts;
  }

  async topToolsSince(since: Date, limit = 5) {
    const counts: Record<string, number> = {};
    for (const execution of this.executions) {
      const executedAt = execution['executedAt'] as Date;
      if (executedAt < since) continue;
      const toolName = execution['toolName'] as string;
      counts[toolName] = (counts[toolName] ?? 0) + 1;
    }
    return Object.entries(counts)
      .map(([toolName, count]) => ({ toolName, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, limit);
  }

  seed(data: Record<string, unknown>) {
    this.executions.push({ id: randomUUID(), ...data, schemaVersion: 1 });
  }
}

class InMemoryAlertRuleRepository {
  private rules: Array<Record<string, unknown>> = [];

  async findById(id: string) {
    return this.rules.find((r) => r['id'] === id) ?? null;
  }

  async findActive() {
    return this.rules.filter((r) => r['isActive'] !== false);
  }

  async findAll() {
    return [...this.rules];
  }

  async upsert(rule: Record<string, unknown>) {
    const idx = this.rules.findIndex((r) => r['id'] === rule['id']);
    if (idx >= 0) {
      this.rules[idx] = rule;
    } else {
      this.rules.push(rule);
    }
    return rule;
  }

  async deactivate(id: string) {
    const rule = this.rules.find((r) => r['id'] === id);
    if (rule) rule['isActive'] = false;
  }
}

describe('ControlModule (e2e)', () => {
  let app: INestApplication;
  let agentRunModel: Model<AgentRunDocument>;
  let evalRunRepo: InMemoryEvalRunRepository;
  let toolExecutionRepo: InMemoryToolExecutionRepository;

  beforeAll(async () => {
    evalRunRepo = new InMemoryEvalRunRepository();
    toolExecutionRepo = new InMemoryToolExecutionRepository();

    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    })
      .overrideProvider(KNOWLEDGE_REPOSITORY).useClass(InMemoryKnowledgeRepository)
      .overrideProvider(EMBEDDING_SERVICE).useClass(StubEmbeddingService)
      .overrideProvider(LLM_CACHE_REPOSITORY).useClass(InMemoryLlmCacheRepository)
      .overrideProvider(QUERY_LOG_REPOSITORY).useClass(InMemoryQueryLogRepository)
      .overrideProvider(DOCUMENT_INDEX_REPOSITORY).useClass(InMemoryDocumentIndexRepository)
      .overrideProvider(CONVERSATION_REPOSITORY).useClass(InMemoryConversationRepository)
      .overrideProvider(PROMPT_TEMPLATE_REPOSITORY).useClass(InMemoryPromptTemplateRepository)
      .overrideProvider(AGENT_RUN_REPOSITORY).useClass(InMemoryAgentRunRepository)
      .overrideProvider(AGENT_STEP_REPOSITORY).useClass(InMemoryAgentStepRepository)
      .overrideProvider(AGENT_DEFINITION_REPOSITORY).useClass(InMemoryAgentDefinitionRepository)
      .overrideProvider(AGENT_MEMORY_REPOSITORY).useClass(InMemoryAgentMemoryRepository)
      .overrideProvider(EVAL_DATASET_REPOSITORY).useClass(InMemoryEvalDatasetRepository)
      .overrideProvider(EVAL_RUN_REPOSITORY).useValue(evalRunRepo)
      .overrideProvider(TOOL_EXECUTION_REPOSITORY).useValue(toolExecutionRepo)
      .overrideProvider(ALERT_RULE_REPOSITORY).useClass(InMemoryAlertRuleRepository)
      .overrideProvider(GroqClientService).useClass(StubGroqClientService)
      .compile();

    app = moduleFixture.createNestApplication();
    app.useGlobalPipes(
      new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true }),
    );
    app.useGlobalFilters(new AllExceptionsFilter());
    app.useGlobalInterceptors(new LoggingInterceptor());
    await app.init();

    agentRunModel = moduleFixture.get<Model<AgentRunDocument>>(getModelToken(AgentRun.name));
    await agentRunModel.deleteMany({});

    const now = Date.now();
    await agentRunModel.create([
      {
        conversationId: 'conv-1',
        status: 'completed',
        triggeredBy: 'supervisor_agent',
        totalIterations: 3,
        totalTokens: 120,
        totalLatencyMs: 1500,
        toolsUsed: ['search_documents', 'summarize_sources'],
        startedAt: new Date(now - 5000),
        finishedAt: new Date(now - 3500),
        metadata: {},
        schemaVersion: 1,
      },
      {
        conversationId: 'conv-2',
        status: 'failed',
        triggeredBy: 'knowledge_agent',
        totalIterations: 2,
        totalTokens: 90,
        totalLatencyMs: 52000,
        toolsUsed: ['search_documents'],
        startedAt: new Date(now - 7000),
        finishedAt: new Date(now - 1000),
        metadata: { guardrailBlocked: true },
        schemaVersion: 1,
      },
    ]);

    toolExecutionRepo.seed({
      runId: 'run-1',
      stepId: 'step-1',
      agentId: 'knowledge_agent',
      toolName: 'search_documents',
      toolArgs: { query: 'atlas' },
      status: 'success',
      latencyMs: 120,
      result: 'ok',
      executedAt: new Date(now - 4000),
    });
    toolExecutionRepo.seed({
      runId: 'run-2',
      stepId: 'step-2',
      agentId: 'knowledge_agent',
      toolName: 'search_documents',
      toolArgs: { query: 'mongo' },
      status: 'error',
      latencyMs: 300,
      errorMessage: 'timeout',
      executedAt: new Date(now - 3000),
    });
    toolExecutionRepo.seed({
      runId: 'run-1',
      stepId: 'step-3',
      agentId: 'supervisor_agent',
      toolName: 'summarize_sources',
      toolArgs: {},
      status: 'success',
      latencyMs: 80,
      result: 'summary',
      executedAt: new Date(now - 2000),
    });

    evalRunRepo.seed({
      id: 'eval-1',
      datasetId: 'core-regression',
      datasetVersion: '1.0.0',
      status: 'completed',
      triggeredBy: 'ci',
      totalCases: 25,
      passedCases: 10,
      failedCases: 15,
      aggregateScore: {
        faithfulness: 0.4,
        relevance: 0.3,
        completeness: 0.2,
        citationCoverage: 0.2,
        toolSuccess: 0.5,
        guardrailCompliance: 0.8,
        latencyBudget: 0.4,
        overallScore: 0.2,
      },
      startedAt: new Date(now - 10000),
      finishedAt: new Date(now - 9000),
      durationMs: 1000,
      schemaVersion: 1,
    });
  }, 60_000);

  afterAll(async () => {
    await app?.close();
  });

  describe('GET /control/dashboard', () => {
    it('should return operational metrics snapshot', async () => {
      const res = await request(app.getHttpServer())
        .get('/control/dashboard')
        .expect(200);

      expect(res.body).toHaveProperty('period', 'last_24h');
      expect(res.body).toHaveProperty('totalRuns', 2);
      expect(res.body).toHaveProperty('avgLatencyMs');
      expect(res.body).toHaveProperty('p95LatencyMs');
      expect(res.body).toHaveProperty('totalToolExecutions', 3);
      expect(res.body.runsByStatus.completed).toBe(1);
      expect(res.body.runsByStatus.failed).toBe(1);
      expect(res.body.toolExecutionsByStatus.success).toBe(2);
      expect(res.body.toolExecutionsByStatus.error).toBe(1);
      expect(Array.isArray(res.body.topTools)).toBe(true);
      expect(res.body.topTools[0].toolName).toBe('search_documents');
      expect(res.body.guardrailBlocks).toBe(1);
      expect(res.body.lastEvalScore.overallScore).toBe(0.2);
    });

    it('should accept period query param', async () => {
      const res = await request(app.getHttpServer())
        .get('/control/dashboard')
        .query({ period: 'last_7d' })
        .expect(200);

      expect(res.body.period).toBe('last_7d');
    });

    it('should reject invalid period', async () => {
      await request(app.getHttpServer())
        .get('/control/dashboard')
        .query({ period: 'forever' })
        .expect(400);
    });
  });

  describe('GET /control/health', () => {
    it('should return critical when active alerts are triggered', async () => {
      const res = await request(app.getHttpServer())
        .get('/control/health')
        .expect(200);

      expect(res.body.status).toBe('critical');
      expect(Array.isArray(res.body.alerts)).toBe(true);
      expect(res.body.alerts.length).toBeGreaterThan(0);
      expect(res.body.alerts.some((alert: { metric: string }) => alert.metric === 'eval_overall_score')).toBe(true);
    });
  });
});
