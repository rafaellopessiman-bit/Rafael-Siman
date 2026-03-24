import { Injectable, Inject } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  LLM_CACHE_REPOSITORY,
  ILlmCacheRepository,
} from '../../domain/repositories/llm-cache.repository.interface';
import {
  QUERY_LOG_REPOSITORY,
  IQueryLogRepository,
} from '../../domain/repositories/query-log.repository.interface';
import { LlmQueryDto } from '../dtos/llm-query.dto';

@Injectable()
export class QueryLlmUseCase {
  private readonly model: string;

  constructor(
    @Inject(LLM_CACHE_REPOSITORY)
    private readonly cacheRepository: ILlmCacheRepository,
    @Inject(QUERY_LOG_REPOSITORY)
    private readonly queryLogRepository: IQueryLogRepository,
    private readonly configService: ConfigService,
  ) {
    this.model = this.configService.get<string>(
      'GROQ_MODEL',
      'llama-3.3-70b-versatile',
    );
  }

  async execute(
    dto: LlmQueryDto,
  ): Promise<{ cached: boolean; response: string | null }> {
    const cachedResponse = await this.cacheRepository.getCached(dto.queryHash);

    if (cachedResponse) {
      return { cached: true, response: cachedResponse };
    }

    if (dto.response) {
      await this.cacheRepository.setCache(
        dto.queryHash,
        dto.response,
        dto.model ?? this.model,
      );
    }

    if (dto.query) {
      await this.queryLogRepository.logQuery({
        query: dto.query,
        response: dto.response,
        model: dto.model ?? this.model,
        sourcesUsed: dto.sourcesUsed,
        tokensUsed: dto.tokensUsed,
        latencyMs: dto.latencyMs,
      });
    }

    return { cached: false, response: dto.response ?? null };
  }
}
