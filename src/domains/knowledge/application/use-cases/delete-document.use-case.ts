import { Injectable, Inject } from '@nestjs/common';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../domain/repositories/knowledge.repository.interface';

@Injectable()
export class DeleteDocumentUseCase {
  constructor(
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepository: IKnowledgeRepository,
  ) {}

  async execute(sourceFile: string): Promise<number> {
    return this.knowledgeRepository.deleteBySourceFile(sourceFile);
  }
}
