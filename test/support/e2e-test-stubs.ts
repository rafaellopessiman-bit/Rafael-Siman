import { INestApplication, ValidationPipe } from '@nestjs/common';
import { randomUUID } from 'crypto';
import { AllExceptionsFilter } from '../../src/shared/filters/all-exceptions.filter';
import { LoggingInterceptor } from '../../src/shared/interceptors/logging.interceptor';
import { MetricsService } from '../../src/shared/telemetry/metrics.service';

export class InMemoryKnowledgeRepository {
  private docs: Array<Record<string, unknown>> = [];

  async create(data: Record<string, unknown>) {
    const doc = {
      _id: randomUUID(),
      ...data,
      charCount:
        typeof data['content'] === 'string'
          ? (data['content'] as string).length
          : 0,
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      schemaVersion: 1,
    };
    this.docs.push(doc);
    return doc;
  }

  async findBySourceFile(sourceFile: string) {
    return this.docs.filter((doc) => doc['sourceFile'] === sourceFile);
  }

  async searchText(query: string, limit: number) {
    const normalizedQuery = query.toLowerCase().trim();
    const tokens = normalizedQuery.split(/\s+/).filter((token) => token.length >= 3);

    return this.docs
      .filter((doc) => {
        const content = String(doc['content'] ?? '').toLowerCase();
        const sourceFile = String(doc['sourceFile'] ?? '').toLowerCase();

        if (!normalizedQuery) {
          return true;
        }

        if (content.includes(normalizedQuery) || sourceFile.includes(normalizedQuery)) {
          return true;
        }

        return tokens.some((token) => content.includes(token) || sourceFile.includes(token));
      })
      .slice(0, limit);
  }

  async vectorSearch(_embedding: number[], limit: number) {
    return this.docs.slice(0, limit);
  }

  async deleteBySourceFile(sourceFile: string) {
    const before = this.docs.length;
    this.docs = this.docs.filter((doc) => doc['sourceFile'] !== sourceFile);
    return before - this.docs.length;
  }

  async findPaginated(skip: number, limit: number) {
    return this.docs.slice(skip, skip + limit);
  }

  async countAll() {
    return this.docs.length;
  }
}

export class StubEmbeddingService {
  readonly model = 'stub';
  readonly dimensions = 1536;

  async embed() {
    return new Array(this.dimensions).fill(0);
  }

  async embedBatch(texts: string[]) {
    return texts.map(() => new Array(this.dimensions).fill(0));
  }
}

export class InMemoryLlmCacheRepository {
  private readonly cache = new Map<string, string>();

  async getCached(hash: string) {
    return this.cache.get(hash) ?? null;
  }

  async setCache(hash: string, response: string) {
    this.cache.set(hash, response);
  }
}

export class InMemoryQueryLogRepository {
  async logQuery() {}
}

export class InMemoryDocumentIndexRepository {
  async upsertIndex(sourceFile: string, data: Record<string, unknown>) {
    return {
      sourceFile,
      ...data,
      schemaVersion: 1,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  }

  async findPending() {
    return [];
  }

  async findAll() {
    return [];
  }
}

export class ConditionalGroqClientService {
  get isConfigured() {
    return false;
  }

  async chatCompletion(messages: Array<{ content?: string }>) {
    const lastContent = String(messages.at(-1)?.content ?? '');

    if (
      /apenas json/i.test(lastContent) ||
      /json valido/i.test(lastContent) ||
      /somente com o json/i.test(lastContent)
    ) {
      return {
        content: JSON.stringify({ empresa: 'Atlas Local', status: 'ativo' }),
        tokensUsed: 37,
        model: 'stub',
      };
    }

    return {
      content: 'Resposta grounded de teste.',
      tokensUsed: 42,
      model: 'stub',
    };
  }

  async chatCompletionWithTools() {
    return {
      content: '[Agent stub] Resposta do agente de teste.',
      tokensUsed: 50,
      model: 'stub',
      toolCalls: undefined,
    };
  }

  async *chatCompletionStream() {
    yield { token: 'Resposta ', done: false };
    yield { token: 'streamed ', done: false };
    yield { token: 'de teste.', done: false };
    yield { token: '', done: true };
  }
}

export class InMemoryConversationRepository {
  private conversations: Array<Record<string, unknown>> = [];

  async create(data: Record<string, unknown>) {
    const doc = {
      _id: randomUUID(),
      ...data,
      messages: [],
      totalTokens: 0,
      messageCount: 0,
      isActive: true,
      schemaVersion: 1,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this.conversations.push(doc);
    return doc;
  }

  async findById(id: string) {
    return this.conversations.find((conversation) => conversation['_id'] === id) ?? null;
  }

  async findAll() {
    return [...this.conversations];
  }

  async findPaginated(skip: number, limit: number) {
    return [...this.conversations].slice(skip, skip + limit);
  }

  async countAll() {
    return this.conversations.length;
  }

  async appendMessage(conversationId: string, message: Record<string, unknown>) {
    const conversation = this.conversations.find((item) => item['_id'] === conversationId);
    if (!conversation) {
      return null;
    }

    const messages = conversation['messages'] as Array<Record<string, unknown>>;
    messages.push({ ...message, timestamp: new Date() });
    conversation['messageCount'] = messages.length;
    conversation['updatedAt'] = new Date();
    return conversation;
  }

  async addTokens(conversationId: string, tokens: number) {
    const conversation = this.conversations.find((item) => item['_id'] === conversationId);
    if (conversation) {
      conversation['totalTokens'] = Number(conversation['totalTokens'] ?? 0) + tokens;
    }
  }

  async archive(conversationId: string) {
    const conversation = this.conversations.find((item) => item['_id'] === conversationId);
    if (conversation) {
      conversation['isActive'] = false;
    }
  }
}

export class InMemoryPromptTemplateRepository {
  private templates: Array<Record<string, unknown>> = [];

  async create(data: Record<string, unknown>) {
    const doc = {
      ...data,
      isActive: true,
      schemaVersion: 1,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this.templates.push(doc);
    return doc;
  }

  async findBySlug(slug: string) {
    return this.templates.find((template) => template['slug'] === slug) ?? null;
  }

  async findAll() {
    return [...this.templates];
  }

  async update(slug: string, data: Record<string, unknown>) {
    const template = this.templates.find((item) => item['slug'] === slug);
    if (!template) {
      return null;
    }

    Object.assign(template, data, { updatedAt: new Date() });
    return template;
  }

  async deactivate(slug: string) {
    const template = this.templates.find((item) => item['slug'] === slug);
    if (template) {
      template['isActive'] = false;
    }
  }
}

export class InMemoryAgentRunRepository {
  private runs: Array<Record<string, unknown>> = [];

  async create(data: Record<string, unknown>) {
    const doc = {
      _id: randomUUID(),
      ...data,
      totalIterations: 0,
      totalTokens: 0,
      totalLatencyMs: 0,
      toolsUsed: [],
      startedAt: new Date(),
      schemaVersion: 1,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this.runs.push(doc);
    return doc;
  }

  async finalize(runId: string, data: Record<string, unknown>) {
    const run = this.runs.find((item) => item['_id'] === runId);
    if (!run) {
      return null;
    }

    Object.assign(run, data, { finishedAt: new Date(), updatedAt: new Date() });
    return run;
  }

  async findById(runId: string) {
    return this.runs.find((item) => item['_id'] === runId) ?? null;
  }

  async findByConversation(conversationId: string, limit = 20, skip = 0) {
    return this.runs.filter((item) => item['conversationId'] === conversationId).slice(skip, skip + limit);
  }

  async findRecent(limit = 20, skip = 0) {
    return [...this.runs].reverse().slice(skip, skip + limit);
  }

  async countRecent() {
    return this.runs.length;
  }

  async countByConversation(conversationId: string) {
    return this.runs.filter((item) => item['conversationId'] === conversationId).length;
  }
}

export class InMemoryAgentStepRepository {
  private steps: Array<Record<string, unknown>> = [];

  async create(data: Record<string, unknown>) {
    const doc = {
      ...data,
      schemaVersion: 1,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this.steps.push(doc);
    return doc;
  }

  async findByRun(runId: string) {
    return this.steps.filter((step) => step['runId'] === runId);
  }
}

export class InMemoryAgentDefinitionRepository {
  private definitions: Array<Record<string, unknown>> = [];

  async findById(id: string) {
    return this.definitions.find((definition) => definition['id'] === id) ?? null;
  }

  async findAll() {
    return [...this.definitions];
  }

  async findActive() {
    return this.definitions.filter((definition) => definition['isActive'] !== false);
  }

  async upsert(data: Record<string, unknown>) {
    const index = this.definitions.findIndex((definition) => definition['id'] === data['id']);
    const doc = {
      ...data,
      schemaVersion: 1,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    if (index >= 0) {
      this.definitions[index] = doc;
    } else {
      this.definitions.push(doc);
    }

    return doc;
  }
}

export class InMemoryAgentMemoryRepository {
  private memories: Array<Record<string, unknown>> = [];

  async findByConversationAndAgent(conversationId: string, agentId: string) {
    return (
      this.memories.find(
        (memory) =>
          memory['conversationId'] === conversationId && memory['agentId'] === agentId,
      ) ?? null
    );
  }

  async upsert(data: Record<string, unknown>) {
    const index = this.memories.findIndex(
      (memory) =>
        memory['conversationId'] === data['conversationId'] &&
        memory['agentId'] === data['agentId'],
    );
    const doc = {
      ...data,
      schemaVersion: 1,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    if (index >= 0) {
      this.memories[index] = doc;
    } else {
      this.memories.push(doc);
    }

    return doc;
  }

  async findRecent(limit = 10) {
    return [...this.memories].reverse().slice(0, limit);
  }
}

export class InMemoryEvalDatasetRepository {
  async findById() {
    return null;
  }

  async findAll() {
    return [];
  }

  async findRegression() {
    return [];
  }

  async upsert(dataset: Record<string, unknown>) {
    return dataset;
  }
}

export class InMemoryEvalRunRepository {
  private runs: Array<Record<string, unknown>> = [];

  async create(data: Record<string, unknown>) {
    const doc = { ...data, schemaVersion: 1, createdAt: new Date(), updatedAt: new Date() };
    this.runs.push(doc);
    return doc;
  }

  async findById(id: string) {
    return this.runs.find((r) => r['evalRunId'] === id || r['id'] === id) ?? null;
  }

  async findByDataset(datasetId: string, limit = 20, skip = 0) {
    return this.runs.filter((r) => r['datasetId'] === datasetId).slice(skip, skip + limit);
  }

  async findRecent(limit = 10, skip = 0) {
    return [...this.runs].reverse().slice(skip, skip + limit);
  }

  async update(id: string, data: Record<string, unknown>) {
    const run = this.runs.find((r) => r['evalRunId'] === id || r['id'] === id);
    if (!run) return null;
    Object.assign(run, data, { updatedAt: new Date() });
    return run;
  }

  async countRecent() {
    return this.runs.length;
  }

  async countByDataset(datasetId: string) {
    return this.runs.filter((r) => r['datasetId'] === datasetId).length;
  }
}

export class InMemoryToolExecutionRepository {
  private executions: Array<Record<string, unknown>> = [];

  async create(data: Record<string, unknown>) {
    const doc = {
      id: randomUUID(),
      ...data,
      schemaVersion: 1,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    this.executions.push(doc);
    return doc;
  }

  async findByRun(runId: string) {
    return this.executions.filter((execution) => execution['runId'] === runId);
  }

  async findByAgent(agentId: string, limit = 50) {
    return this.executions.filter((execution) => execution['agentId'] === agentId).slice(0, limit);
  }

  async findRecent(limit = 50) {
    return [...this.executions].reverse().slice(0, limit);
  }

  async countByStatusSince(since: Date) {
    const counts: Record<string, number> = {};

    for (const execution of this.executions) {
      const executedAt = execution['executedAt'] as Date;
      if (executedAt < since) {
        continue;
      }

      const status = String(execution['status']);
      counts[status] = (counts[status] ?? 0) + 1;
    }

    return counts;
  }

  async topToolsSince(since: Date, limit = 5) {
    const counts: Record<string, number> = {};

    for (const execution of this.executions) {
      const executedAt = execution['executedAt'] as Date;
      if (executedAt < since) {
        continue;
      }

      const toolName = String(execution['toolName']);
      counts[toolName] = (counts[toolName] ?? 0) + 1;
    }

    return Object.entries(counts)
      .map(([toolName, count]) => ({ toolName, count }))
      .sort((left, right) => right.count - left.count)
      .slice(0, limit);
  }
}

export class InMemoryAlertRuleRepository {
  private rules: Array<Record<string, unknown>> = [];

  async findById(id: string) {
    return this.rules.find((rule) => rule['id'] === id) ?? null;
  }

  async findActive() {
    return this.rules.filter((rule) => rule['isActive'] !== false);
  }

  async findAll() {
    return [...this.rules];
  }

  async upsert(rule: Record<string, unknown>) {
    const index = this.rules.findIndex((item) => item['id'] === rule['id']);
    if (index >= 0) {
      this.rules[index] = rule;
    } else {
      this.rules.push(rule);
    }

    return rule;
  }

  async deactivate(id: string) {
    const rule = this.rules.find((item) => item['id'] === id);
    if (rule) {
      rule['isActive'] = false;
    }
  }
}

export function applyTestAppConfig(app: INestApplication): void {
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );
  app.useGlobalFilters(new AllExceptionsFilter());
  app.useGlobalInterceptors(new LoggingInterceptor(app.get(MetricsService)));
}
