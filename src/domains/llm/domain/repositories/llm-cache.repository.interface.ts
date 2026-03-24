export const LLM_CACHE_REPOSITORY = Symbol('LLM_CACHE_REPOSITORY');

export interface ILlmCacheRepository {
  getCached(queryHash: string): Promise<string | null>;
  setCache(queryHash: string, response: string, model: string): Promise<void>;
}
