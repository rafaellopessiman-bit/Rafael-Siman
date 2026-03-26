import { Injectable, Inject, Logger } from '@nestjs/common';
import {
  LLM_CACHE_REPOSITORY,
  ILlmCacheRepository,
} from '../../domain/repositories/llm-cache.repository.interface';
import {
  QUERY_LOG_REPOSITORY,
  IQueryLogRepository,
} from '../../domain/repositories/query-log.repository.interface';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../../knowledge/domain/repositories/knowledge.repository.interface';
import {
  EMBEDDING_SERVICE,
  IEmbeddingService,
} from '../../../knowledge/domain/services/embedding.service';
import { GroqClientService } from '../../infrastructure/groq/groq-client.service';
import { AskQueryDto, AskQueryResult } from '../dtos/ask-query.dto';
import { AskCacheService } from '../../../../shared/cache/ask-cache.service';
import { MetricsService } from '../../../../shared/telemetry/metrics.service';
import { ConfigService } from '@nestjs/config';

const SYSTEM_PROMPT = `Você é um assistente especializado em análise de documentos.
Responda APENAS com base no contexto fornecido entre as tags <context>.
Se a resposta não puder ser encontrada no contexto, diga explicitamente que não encontrou informação suficiente.
Responda em português. Seja conciso e preciso.`;

/**
 * RAG Use Case — Retrieval-Augmented Generation.
 *
 * Fluxo:
 *  1. Gera hash da query para cache lookup (SHA-256 dos primeiros 64 chars)
 *  2. Verifica cache LLM — se hit, retorna imediatamente
 *  3. Recupera top-K chunks relevantes (text ou vector search)
 *  4. Monta prompt com contexto
 *  5. Chama Groq API
 *  6. Grava resultado no cache + log
 */
@Injectable()
export class AskDocumentsUseCase {
  private readonly logger = new Logger(AskDocumentsUseCase.name);
  private readonly vectorSearchEnabled: boolean;

  constructor(
    @Inject(LLM_CACHE_REPOSITORY)
    private readonly cacheRepository: ILlmCacheRepository,
    @Inject(QUERY_LOG_REPOSITORY)
    private readonly queryLogRepository: IQueryLogRepository,
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepository: IKnowledgeRepository,
    @Inject(EMBEDDING_SERVICE)
    private readonly embeddingService: IEmbeddingService,
    private readonly groqClient: GroqClientService,
    private readonly askCacheService: AskCacheService,
    private readonly metricsService: MetricsService,
    private readonly configService: ConfigService,
  ) {
    this.vectorSearchEnabled =
      this.configService.get<string>('ATLAS_VECTOR_SEARCH_ENABLED', 'false') === 'true';
  }

  async execute(dto: AskQueryDto): Promise<AskQueryResult> {
    const topK = dto.topK ?? 5;
    const queryHash = this.askCacheService.buildKey(dto.query, topK);
    const startMs = Date.now();

    // 1. Cache hit
    const cached = await this.cacheRepository.getCached(queryHash);
    if (cached) {
      this.metricsService.cacheHits.inc({ result: 'hit' });
      this.logger.log(`Cache hit para query hash ${queryHash}`);
      return {
        answer: cached,
        sources: [],
        cached: true,
        tokensUsed: 0,
        latencyMs: Date.now() - startMs,
      };
    }

    // 2. Recupera contexto
    let chunks: { content: string; sourceFile?: string }[];

    if (this.vectorSearchEnabled) {
      const embedding = await this.embeddingService.embed(dto.query);
      chunks = await this.knowledgeRepository.vectorSearch(embedding, topK);
    } else {
      chunks = await this.knowledgeRepository.searchText(dto.query, topK);
    }

    const contextText = chunks
      .map((c, i) => `[${i + 1}] ${c.content}`)
      .join('\n\n');

    const sources = [
      ...new Set(
        chunks
          .map((c) => c.sourceFile)
          .filter((s): s is string => Boolean(s)),
      ),
    ];

    // 3. Gera resposta via Groq
    const result = await this.groqClient.chatCompletion([
      { role: 'system', content: SYSTEM_PROMPT },
      {
        role: 'user',
        content: `<context>\n${contextText || 'Nenhum documento encontrado.'}\n</context>\n\nPergunta: ${dto.query}`,
      },
    ]);

    const latencyMs = Date.now() - startMs;

    // 4. Persiste no cache
    this.metricsService.cacheHits.inc({ result: 'miss' });
    await this.cacheRepository.setCache(queryHash, result.content, result.model);

    // 5. Registra no log
    await this.queryLogRepository.logQuery({
      query: dto.query,
      response: result.content,
      model: result.model,
      sourcesUsed: sources,
      tokensUsed: result.tokensUsed,
      latencyMs,
    });

    return {
      answer: result.content,
      sources,
      cached: false,
      tokensUsed: result.tokensUsed,
      latencyMs,
    };
  }

}
