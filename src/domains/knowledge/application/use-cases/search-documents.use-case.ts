import { Injectable, Inject } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { KnowledgeDocumentDocument } from '../../infrastructure/persistence/knowledge-document.schema';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../domain/repositories/knowledge.repository.interface';
import {
  EMBEDDING_SERVICE,
  IEmbeddingService,
} from '../../domain/services/embedding.service';

@Injectable()
export class SearchDocumentsUseCase {
  private readonly vectorSearchEnabled: boolean;

  constructor(
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepository: IKnowledgeRepository,
    @Inject(EMBEDDING_SERVICE)
    private readonly embeddingService: IEmbeddingService,
    private readonly configService: ConfigService,
  ) {
    this.vectorSearchEnabled =
      this.configService.get<string>('ATLAS_VECTOR_SEARCH_ENABLED', 'false') === 'true';
  }

  async execute(query: string, limit = 5): Promise<KnowledgeDocumentDocument[]> {
    if (!this.vectorSearchEnabled) {
      return this.knowledgeRepository.searchText(query, limit);
    }

    const queryEmbedding = await this.embeddingService.embed(query);
    return this.knowledgeRepository.vectorSearch(queryEmbedding, limit);
  }
}
