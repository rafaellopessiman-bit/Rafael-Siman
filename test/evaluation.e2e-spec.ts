import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
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
import { GroqClientService } from '../src/domains/llm/infrastructure/groq/groq-client.service';
import { AllExceptionsFilter } from '../src/shared/filters/all-exceptions.filter';
import { LoggingInterceptor } from '../src/shared/interceptors/logging.interceptor';
import { IEvalDataset } from '../src/domains/evaluation/domain/interfaces/eval-dataset.interface';
import { IEvalRun } from '../src/domains/evaluation/domain/interfaces/eval-run.interface';
import { randomUUID } from 'crypto';

// ── Inline stubs (reused from app.e2e-spec.ts pattern) ────────────────────

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
  async setCache() { /* no-op */ }
}

class InMemoryQueryLogRepository {
  async logQuery() { /* no-op */ }
}

class InMemoryDocumentIndexRepository {
  private docs: Array<Record<string, unknown>> = [];
  async upsertIndex(sourceFile: string, data: Record<string, unknown>) {
    const doc = { sourceFile, ...data, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() };
    const idx = this.docs.findIndex((d) => d['sourceFile'] === sourceFile);
    if (idx >= 0) { this.docs[idx] = doc; } else { this.docs.push(doc); }
    return doc;
  }
  async findPending() { return []; }
  async findAll() { return [...this.docs]; }
}

class StubGroqClientService {
  get isConfigured() { return false; }
  async chatCompletion() { return { content: '[stub]', tokensUsed: 42, model: 'stub' }; }
  async chatCompletionWithTools() { return { content: '[agent stub]', tokensUsed: 50, model: 'stub', toolCalls: undefined }; }
}

class InMemoryConversationRepository {
  private convs: Array<Record<string, unknown>> = [];
  private counter = 0;
  async create(data: Record<string, unknown>) {
    const c = { _id: `conv-${++this.counter}`, ...data, messages: [], totalTokens: 0, messageCount: 0, isActive: true, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() };
    this.convs.push(c);
    return c;
  }
  async findById(id: string) { return this.convs.find((c) => c['_id'] === id) ?? null; }
  async findAll() { return this.convs.filter((c) => c['isActive'] !== false); }
  async findPaginated(skip: number, limit: number) { return this.convs.filter((c) => c['isActive'] !== false).slice(skip, skip + limit); }
  async countAll() { return this.convs.filter((c) => c['isActive'] !== false).length; }
  async appendMessage(conversationId: string, msg: Record<string, unknown>) {
    const conv = this.convs.find((c) => c['_id'] === conversationId);
    if (!conv) return null;
    (conv['messages'] as unknown[]).push({ ...msg, timestamp: new Date() });
    conv['messageCount'] = (conv['messages'] as unknown[]).length;
    return conv;
  }
  async addTokens(id: string, tokens: number) {
    const c = this.convs.find((c) => c['_id'] === id);
    if (c) c['totalTokens'] = (c['totalTokens'] as number) + tokens;
  }
  async archive(id: string) {
    const c = this.convs.find((c) => c['_id'] === id);
    if (c) c['isActive'] = false;
  }
}

class InMemoryPromptTemplateRepository {
  private tpls: Array<Record<string, unknown>> = [];
  async create(data: Record<string, unknown>) { const t = { ...data, isActive: true, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() }; this.tpls.push(t); return t; }
  async findBySlug(slug: string) { return this.tpls.find((t) => t['slug'] === slug && t['isActive'] !== false) ?? null; }
  async findAll() { return this.tpls.filter((t) => t['isActive'] !== false); }
  async update(slug: string, data: Record<string, unknown>) {
    const t = this.tpls.find((t) => t['slug'] === slug);
    if (!t) return null;
    Object.assign(t, data, { updatedAt: new Date() });
    return t;
  }
  async deactivate(slug: string) { const t = this.tpls.find((t) => t['slug'] === slug); if (t) t['isActive'] = false; }
}

class InMemoryAgentRunRepository {
  private runs: Array<Record<string, unknown>> = [];
  private counter = 0;
  async create(data: Record<string, unknown>) { const r = { _id: `run-${++this.counter}`, ...data, totalIterations: 0, totalTokens: 0, totalLatencyMs: 0, toolsUsed: [], startedAt: new Date(), schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() }; this.runs.push(r); return r; }
  async finalize(runId: string, data: Record<string, unknown>) { const r = this.runs.find((r) => r['_id'] === runId); if (!r) return null; Object.assign(r, data, { finishedAt: new Date(), updatedAt: new Date() }); return r; }
  async findById(id: string) { return this.runs.find((r) => r['_id'] === id) ?? null; }
  async findByConversation(conversationId: string, limit = 20, skip = 0) { return this.runs.filter((r) => r['conversationId'] === conversationId).slice(skip, skip + limit); }
  async findRecent(limit = 20, skip = 0) { return this.runs.slice(-limit - skip).reverse().slice(skip, skip + limit); }
  async countRecent() { return this.runs.length; }
  async countByConversation(conversationId: string) { return this.runs.filter((r) => r['conversationId'] === conversationId).length; }
}

class InMemoryAgentStepRepository {
  private steps: Array<Record<string, unknown>> = [];
  async create(data: Record<string, unknown>) { const s = { ...data, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() }; this.steps.push(s); return s; }
  async findByRun(runId: string) { return this.steps.filter((s) => s['runId'] === runId).sort((a, b) => (a['stepNumber'] as number) - (b['stepNumber'] as number)); }
}

class InMemoryAgentDefinitionRepository {
  private defs: Array<Record<string, unknown>> = [];
  async findById(id: string) { return this.defs.find((d) => d['id'] === id) ?? null; }
  async findAll() { return [...this.defs]; }
  async findActive() { return this.defs.filter((d) => d['isActive'] !== false); }
  async upsert(data: Record<string, unknown>) {
    const idx = this.defs.findIndex((d) => d['id'] === data['id']);
    const doc = { ...data, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() };
    if (idx >= 0) { this.defs[idx] = doc; } else { this.defs.push(doc); }
    return doc;
  }
}

class InMemoryAgentMemoryRepository {
  private mems: Array<Record<string, unknown>> = [];
  async findByConversationAndAgent(conversationId: string, agentId: string) { return this.mems.find((m) => m['conversationId'] === conversationId && m['agentId'] === agentId) ?? null; }
  async upsert(data: Record<string, unknown>) {
    const idx = this.mems.findIndex((m) => m['conversationId'] === data['conversationId'] && m['agentId'] === data['agentId']);
    const doc = { ...data, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() };
    if (idx >= 0) { this.mems[idx] = doc; } else { this.mems.push(doc); }
    return doc;
  }
  async findRecent(limit = 10) { return this.mems.slice(-limit).reverse(); }
}

// ── In-memory Eval Dataset Repository ─────────────────────────────────────
class InMemoryEvalDatasetRepository {
  private datasets: IEvalDataset[] = [];

  async findById(id: string): Promise<IEvalDataset | null> {
    return this.datasets.find((d) => d.id === id) ?? null;
  }

  async findAll(): Promise<IEvalDataset[]> {
    return [...this.datasets];
  }

  async findRegression(): Promise<IEvalDataset[]> {
    return this.datasets.filter((d) => d.isRegression);
  }

  async upsert(dataset: IEvalDataset): Promise<IEvalDataset> {
    const idx = this.datasets.findIndex((d) => d.id === dataset.id);
    if (idx >= 0) {
      this.datasets[idx] = { ...dataset, updatedAt: new Date() };
    } else {
      this.datasets.push({ ...dataset });
    }
    return this.datasets.find((d) => d.id === dataset.id)!;
  }
}

// ── In-memory Eval Run Repository ──────────────────────────────────────────
class InMemoryEvalRunRepository {
  private runs: IEvalRun[] = [];

  async create(run: Partial<IEvalRun>): Promise<IEvalRun> {
    const doc = {
      id: run.id ?? randomUUID(),
      datasetId: run.datasetId ?? '',
      datasetVersion: run.datasetVersion ?? '1.0.0',
      status: run.status ?? 'pending',
      triggeredBy: run.triggeredBy ?? 'test',
      totalCases: run.totalCases ?? 0,
      passedCases: run.passedCases ?? 0,
      failedCases: run.failedCases ?? 0,
      aggregateScore: run.aggregateScore,
      startedAt: run.startedAt ?? new Date(),
      finishedAt: run.finishedAt,
      durationMs: run.durationMs,
      schemaVersion: 1,
    } as IEvalRun;
    this.runs.push(doc);
    return doc;
  }

  async findById(id: string): Promise<IEvalRun | null> {
    return this.runs.find((r) => r.id === id) ?? null;
  }

  async findByDataset(datasetId: string, limit = 20, skip = 0): Promise<IEvalRun[]> {
    return this.runs.filter((r) => r.datasetId === datasetId).slice(skip, skip + limit);
  }

  async findRecent(limit = 10, skip = 0): Promise<IEvalRun[]> {
    return [...this.runs].reverse().slice(skip, skip + limit);
  }

  async update(id: string, data: Partial<IEvalRun>): Promise<IEvalRun | null> {
    const idx = this.runs.findIndex((r) => r.id === id);
    if (idx < 0) return null;
    this.runs[idx] = { ...this.runs[idx], ...data };
    return this.runs[idx];
  }

  async countRecent(): Promise<number> {
    return this.runs.length;
  }

  async countByDataset(datasetId: string): Promise<number> {
    return this.runs.filter((r) => r.datasetId === datasetId).length;
  }
}

// ── Seed dataset fixture ───────────────────────────────────────────────────
const TEST_DATASET_ID = 'test-dataset-001';
const seedDataset: IEvalDataset = {
  id: TEST_DATASET_ID,
  name: 'Test Dataset',
  description: 'Dataset para testes e2e',
  version: '1.0.0',
  isRegression: false,
  schemaVersion: 1,
  createdAt: new Date(),
  updatedAt: new Date(),
  cases: [
    {
      id: randomUUID(),
      datasetId: TEST_DATASET_ID,
      input: 'Teste básico de avaliação',
      expectedKeywords: ['teste'],
      forbiddenKeywords: ['falha'],
      expectedAgents: ['knowledge'],
      requiresCitations: false,
      latencyBudgetMs: 5000,
      actualOutput: 'Este é um teste de avaliação do sistema.',
      actualAgents: ['knowledge'],
      actualLatencyMs: 1000,
    },
    {
      id: randomUUID(),
      datasetId: TEST_DATASET_ID,
      input: 'Pergunta com citação obrigatória',
      expectedKeywords: ['atlas', 'local'],
      forbiddenKeywords: [],
      expectedAgents: ['knowledge'],
      requiresCitations: true,
      latencyBudgetMs: 5000,
      actualOutput: 'O Atlas Local é um sistema. (fonte: docs/README.md)',
      actualAgents: ['knowledge'],
      actualLatencyMs: 2000,
    },
  ],
};

// ─────────────────────────────────────────────────────────────────────────────

describe('EvaluationModule (e2e)', () => {
  let app: INestApplication;
  let evalDatasetRepo: InMemoryEvalDatasetRepository;
  let evalRunRepo: InMemoryEvalRunRepository;

  beforeAll(async () => {
    evalDatasetRepo = new InMemoryEvalDatasetRepository();
    evalRunRepo = new InMemoryEvalRunRepository();

    // Pre-seed test dataset
    await evalDatasetRepo.upsert(seedDataset);

    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    })
      // ── Existing domain stubs ──
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
      .overrideProvider(GroqClientService).useClass(StubGroqClientService)
      // ── Evaluation domain stubs ──
      .overrideProvider(EVAL_DATASET_REPOSITORY).useValue(evalDatasetRepo)
      .overrideProvider(EVAL_RUN_REPOSITORY).useValue(evalRunRepo)
      .compile();

    app = moduleFixture.createNestApplication();
    app.useGlobalPipes(
      new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true }),
    );
    app.useGlobalFilters(new AllExceptionsFilter());
    app.useGlobalInterceptors(new LoggingInterceptor());
    await app.init();
  }, 60_000);

  afterAll(async () => {
    await app?.close();
  });

  // ── POST /eval/run ─────────────────────────────────────────────────────────

  describe('POST /eval/run', () => {
    it('should create and complete an eval run for a seeded dataset', async () => {
      const res = await request(app.getHttpServer())
        .post('/eval/run')
        .send({ datasetId: TEST_DATASET_ID, triggeredBy: 'e2e-test' })
        .expect(201);

      expect(res.body).toHaveProperty('id');
      expect(res.body).toHaveProperty('datasetId', TEST_DATASET_ID);
      expect(res.body).toHaveProperty('status', 'completed');
      expect(res.body).toHaveProperty('totalCases', 2);
      expect(res.body).toHaveProperty('aggregateScore');
      expect(res.body.aggregateScore).toHaveProperty('overallScore');
    });

    it('should return 404 for unknown datasetId', async () => {
      const res = await request(app.getHttpServer())
        .post('/eval/run')
        .send({ datasetId: 'nonexistent-dataset' })
        .expect(404);

      expect(res.body.message).toMatch(/not found/i);
    });

    it('should reject missing datasetId (400)', async () => {
      await request(app.getHttpServer())
        .post('/eval/run')
        .send({})
        .expect(400);
    });

    it('should reject unknown fields (forbidNonWhitelisted)', async () => {
      await request(app.getHttpServer())
        .post('/eval/run')
        .send({ datasetId: TEST_DATASET_ID, hackerField: 'drop table' })
        .expect(400);
    });
  });

  // ── GET /eval/runs ─────────────────────────────────────────────────────────

  describe('GET /eval/runs', () => {
    it('should return recent eval runs as paginated envelope', async () => {
      // Ensure at least one run exists
      await request(app.getHttpServer())
        .post('/eval/run')
        .send({ datasetId: TEST_DATASET_ID });

      const res = await request(app.getHttpServer())
        .get('/eval/runs')
        .expect(200);

      expect(res.body).toHaveProperty('data');
      expect(res.body).toHaveProperty('meta');
      expect(Array.isArray(res.body.data)).toBe(true);
      expect(res.body.data.length).toBeGreaterThan(0);
    });

    it('should respect the limit query param', async () => {
      const res = await request(app.getHttpServer())
        .get('/eval/runs')
        .query({ limit: 1 })
        .expect(200);

      expect(Array.isArray(res.body.data)).toBe(true);
      expect(res.body.data.length).toBeLessThanOrEqual(1);
      expect(res.body.meta.limit).toBe(1);
    });
  });

  // ── GET /eval/runs/:id ─────────────────────────────────────────────────────

  describe('GET /eval/runs/:id', () => {
    let createdRunId: string;

    beforeAll(async () => {
      const res = await request(app.getHttpServer())
        .post('/eval/run')
        .send({ datasetId: TEST_DATASET_ID, triggeredBy: 'e2e-get-by-id' });
      createdRunId = res.body.id as string;
    });

    it('should find eval run by ID', async () => {
      const res = await request(app.getHttpServer())
        .get(`/eval/runs/${createdRunId}`)
        .expect(200);

      expect(res.body).toHaveProperty('id', createdRunId);
      expect(res.body).toHaveProperty('status', 'completed');
    });

    it('should return 404 for unknown run ID', async () => {
      await request(app.getHttpServer())
        .get('/eval/runs/not-a-real-id')
        .expect(404);
    });
  });

  // ── GET /eval/runs/dataset/:datasetId ─────────────────────────────────────

  describe('GET /eval/runs/dataset/:datasetId', () => {
    it('should list runs for a specific dataset', async () => {
      const res = await request(app.getHttpServer())
        .get(`/eval/runs/dataset/${TEST_DATASET_ID}`)
        .expect(200);

      expect(res.body).toHaveProperty('data');
      expect(res.body).toHaveProperty('meta');
      expect(Array.isArray(res.body.data)).toBe(true);
      for (const run of res.body.data) {
        expect(run.datasetId).toBe(TEST_DATASET_ID);
      }
    });
  });

  // ── EvalEngine: score quality ───────────────────────────────────────────────

  describe('Eval run quality checks', () => {
    it('should produce overallScore between 0 and 1', async () => {
      const res = await request(app.getHttpServer())
        .post('/eval/run')
        .send({ datasetId: TEST_DATASET_ID })
        .expect(201);

      const { aggregateScore } = res.body as { aggregateScore: { overallScore: number } };
      expect(aggregateScore.overallScore).toBeGreaterThanOrEqual(0);
      expect(aggregateScore.overallScore).toBeLessThanOrEqual(1);
    });

    it('should count passedCases + failedCases = totalCases', async () => {
      const res = await request(app.getHttpServer())
        .post('/eval/run')
        .send({ datasetId: TEST_DATASET_ID })
        .expect(201);

      const { totalCases, passedCases, failedCases } = res.body as { totalCases: number; passedCases: number; failedCases: number };
      expect(passedCases + failedCases).toBe(totalCases);
    });
  });
});
