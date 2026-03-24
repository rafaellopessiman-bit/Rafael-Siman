import { Injectable, Inject } from '@nestjs/common';
import { KnowledgeDocumentDocument } from '../../infrastructure/persistence/knowledge-document.schema';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../domain/repositories/knowledge.repository.interface';
import { IndexDocumentDto } from '../dtos/index-document.dto';

@Injectable()
export class IndexDocumentUseCase {
  constructor(
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepository: IKnowledgeRepository,
  ) {}

  async execute(dto: IndexDocumentDto): Promise<KnowledgeDocumentDocument> {
    return this.knowledgeRepository.create({
      sourceFile: dto.sourceFile,
      content: dto.content,
      fileType: dto.fileType,
      chunkIndex: dto.chunkIndex,
      metadata: dto.metadata,
    });
  }
}
