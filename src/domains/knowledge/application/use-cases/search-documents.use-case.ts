import { Injectable, Inject } from '@nestjs/common';
import { KnowledgeDocumentDocument } from '../../infrastructure/persistence/knowledge-document.schema';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../domain/repositories/knowledge.repository.interface';

@Injectable()
export class SearchDocumentsUseCase {
  constructor(
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepository: IKnowledgeRepository,
  ) {}

  async execute(query: string, limit = 5): Promise<KnowledgeDocumentDocument[]> {
    return this.knowledgeRepository.searchText(query, limit);
  }
}
