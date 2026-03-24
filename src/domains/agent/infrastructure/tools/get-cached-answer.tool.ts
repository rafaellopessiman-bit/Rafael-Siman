import { Injectable, Inject, OnModuleInit } from '@nestjs/common';
import {
  IAgentTool,
  ToolParametersSchema,
} from '../../domain/interfaces/agent-tool.interface';
import { ToolRegistryService } from '../../domain/services/tool-registry.service';
import {
  LLM_CACHE_REPOSITORY,
  ILlmCacheRepository,
} from '../../../llm/domain/repositories/llm-cache.repository.interface';

/**
 * Tool: get_cached_answer
 *
 * Permite ao agente consultar o cache de respostas LLM
 * para evitar reprocessamento de perguntas já respondidas.
 */
@Injectable()
export class GetCachedAnswerTool implements IAgentTool, OnModuleInit {
  readonly name = 'get_cached_answer';
  readonly description =
    'Consulta o cache de respostas anteriores do LLM por hash da query. Retorna a resposta cacheada se existir.';
  readonly parameters: ToolParametersSchema = {
    type: 'object',
    properties: {
      queryHash: {
        type: 'string',
        description: 'Hash SHA-256 (16 chars) da query a consultar no cache',
        required: true,
      },
    },
    required: ['queryHash'],
  };

  constructor(
    private readonly registry: ToolRegistryService,
    @Inject(LLM_CACHE_REPOSITORY)
    private readonly cacheRepo: ILlmCacheRepository,
  ) {}

  onModuleInit(): void {
    this.registry.register(this);
  }

  async execute(params: Record<string, unknown>): Promise<string> {
    const queryHash = String(params.queryHash ?? '');
    if (!queryHash) {
      return 'Parâmetro "queryHash" é obrigatório.';
    }

    const cached = await this.cacheRepo.getCached(queryHash);
    if (cached) {
      return `Resposta em cache encontrada:\n${cached}`;
    }
    return 'Nenhuma resposta em cache para esse hash.';
  }
}
