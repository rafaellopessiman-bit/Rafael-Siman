import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import {
  KnowledgeDocument,
  KnowledgeDocumentSchema,
} from './infrastructure/persistence/knowledge-document.schema';
import { MongooseKnowledgeRepository } from './infrastructure/persistence/knowledge.repository';
import { KNOWLEDGE_REPOSITORY } from './domain/repositories/knowledge.repository.interface';
import { KnowledgeController } from './infrastructure/http/knowledge.controller';
import { IndexDocumentUseCase } from './application/use-cases/index-document.use-case';
import { SearchDocumentsUseCase } from './application/use-cases/search-documents.use-case';
import { DeleteDocumentUseCase } from './application/use-cases/delete-document.use-case';
import { FindBySourceFileUseCase } from './application/use-cases/find-by-source-file.use-case';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: KnowledgeDocument.name, schema: KnowledgeDocumentSchema },
    ]),
  ],
  controllers: [KnowledgeController],
  providers: [
    {
      provide: KNOWLEDGE_REPOSITORY,
      useClass: MongooseKnowledgeRepository,
    },
    IndexDocumentUseCase,
    SearchDocumentsUseCase,
    DeleteDocumentUseCase,
    FindBySourceFileUseCase,
  ],
  exports: [KNOWLEDGE_REPOSITORY],
})
export class KnowledgeModule {}
