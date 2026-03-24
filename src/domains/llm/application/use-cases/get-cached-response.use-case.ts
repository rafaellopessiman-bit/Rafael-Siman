import { Injectable, Inject } from '@nestjs/common';
import {
  LLM_CACHE_REPOSITORY,
  ILlmCacheRepository,
} from '../../domain/repositories/llm-cache.repository.interface';

@Injectable()
export class GetCachedResponseUseCase {
  constructor(
    @Inject(LLM_CACHE_REPOSITORY)
    private readonly cacheRepository: ILlmCacheRepository,
  ) {}

  async execute(queryHash: string): Promise<string | null> {
    return this.cacheRepository.getCached(queryHash);
  }
}
