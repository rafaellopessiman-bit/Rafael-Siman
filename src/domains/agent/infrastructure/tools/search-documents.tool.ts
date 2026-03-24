import { Injectable, Inject, OnModuleInit } from '@nestjs/common';
import {
  IAgentTool,
  ToolParametersSchema,
} from '../../domain/interfaces/agent-tool.interface';
import { ToolRegistryService } from '../../domain/services/tool-registry.service';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../../knowledge/domain/repositories/knowledge.repository.interface';
import {
  EMBEDDING_SERVICE,
  IEmbeddingService,
} from '../../../knowledge/domain/services/embedding.service';
import { ConfigService } from '@nestjs/config';

/**
 * Tool: search_documents
 *
 * Permite ao agente buscar chunks de documentos indexados.
 * Usa text search ou vector search conforme configuração.
 */
@Injectable()
export class SearchDocumentsTool implements IAgentTool, OnModuleInit {
  readonly name = 'search_documents';
  readonly description =
    'Busca documentos indexados na base de conhecimento. Retorna os chunks mais relevantes para a query.';
  readonly parameters: ToolParametersSchema = {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description: 'Texto de busca em linguagem natural',
        required: true,
      },
      limit: {
        type: 'number',
        description: 'Máximo de resultados (1-20, padrão: 5)',
      },
    },
    required: ['query'],
  };

  private readonly vectorSearchEnabled: boolean;

  constructor(
    private readonly registry: ToolRegistryService,
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepo: IKnowledgeRepository,
    @Inject(EMBEDDING_SERVICE)
    private readonly embeddingService: IEmbeddingService,
    private readonly configService: ConfigService,
  ) {
    this.vectorSearchEnabled =
      this.configService.get<string>('ATLAS_VECTOR_SEARCH_ENABLED', 'false') === 'true';
  }

  onModuleInit(): void {
    this.registry.register(this);
  }

  async execute(params: Record<string, unknown>): Promise<string> {
    const query = String(params.query ?? '');
    const limit = Math.min(Math.max(Number(params.limit) || 5, 1), 20);

    let chunks: { content: string; sourceFile?: string }[];

    if (this.vectorSearchEnabled) {
      const embedding = await this.embeddingService.embed(query);
      chunks = await this.knowledgeRepo.vectorSearch(embedding, limit);
    } else {
      chunks = await this.knowledgeRepo.searchText(query, limit);
    }

    if (chunks.length === 0) {
      return 'Nenhum documento encontrado para essa busca.';
    }

    return chunks
      .map(
        (c, i) =>
          `[${i + 1}] (fonte: ${c.sourceFile ?? 'desconhecida'})\n${c.content}`,
      )
      .join('\n\n---\n\n');
  }
}
