import { Injectable, Inject } from '@nestjs/common';
import { KnowledgeDocumentDocument } from '../../infrastructure/persistence/knowledge-document.schema';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../domain/repositories/knowledge.repository.interface';
import { IndexDocumentDto } from '../dtos/index-document.dto';
import { ChunkingService } from '../../domain/services/chunking.service';
import {
  EMBEDDING_SERVICE,
  IEmbeddingService,
} from '../../domain/services/embedding.service';

@Injectable()
export class IndexDocumentUseCase {
  constructor(
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepository: IKnowledgeRepository,
    private readonly chunkingService: ChunkingService,
    @Inject(EMBEDDING_SERVICE)
    private readonly embeddingService: IEmbeddingService,
  ) {}

  async execute(
    dto: IndexDocumentDto,
  ): Promise<KnowledgeDocumentDocument[]> {
    const fileType = dto.fileType ?? '.txt';

    // Se chunkIndex já foi fornecido, trata como chunk individual (backward-compat)
    if (dto.chunkIndex !== undefined) {
      const embedding = await this.embeddingService.embed(dto.content);
      const doc = await this.knowledgeRepository.create({
        sourceFile: dto.sourceFile,
        content: dto.content,
        fileType: dto.fileType,
        chunkIndex: dto.chunkIndex,
        metadata: dto.metadata,
        embedding,
      });
      return [doc];
    }

    // Chunking automático + embedding por chunk
    const chunks = this.chunkingService.chunk(fileType, dto.content);

    if (chunks.length === 0) {
      const embedding = await this.embeddingService.embed(dto.content);
      const doc = await this.knowledgeRepository.create({
        sourceFile: dto.sourceFile,
        content: dto.content,
        fileType: dto.fileType,
        chunkIndex: 0,
        metadata: dto.metadata,
        embedding,
      });
      return [doc];
    }

    const embeddings = await this.embeddingService.embedBatch(
      chunks.map((c) => c.text),
    );

    const docs: KnowledgeDocumentDocument[] = [];
    for (let i = 0; i < chunks.length; i++) {
      const doc = await this.knowledgeRepository.create({
        sourceFile: dto.sourceFile,
        content: chunks[i].text,
        fileType: dto.fileType,
        chunkIndex: chunks[i].chunkIndex,
        metadata: dto.metadata,
        embedding: embeddings[i],
      });
      docs.push(doc);
    }

    return docs;
  }
}
