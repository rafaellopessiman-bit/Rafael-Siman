import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import {
  DocumentIndex,
  DocumentIndexSchema,
} from './infrastructure/persistence/document-index.schema';
import { MongooseDocumentIndexRepository } from './infrastructure/persistence/document-index.repository';
import { DOCUMENT_INDEX_REPOSITORY } from './domain/repositories/document-index.repository.interface';
import { UpsertDocumentIndexUseCase } from './application/use-cases/upsert-document-index.use-case';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: DocumentIndex.name, schema: DocumentIndexSchema },
    ]),
  ],
  providers: [
    {
      provide: DOCUMENT_INDEX_REPOSITORY,
      useClass: MongooseDocumentIndexRepository,
    },
    UpsertDocumentIndexUseCase,
  ],
  exports: [DOCUMENT_INDEX_REPOSITORY],
})
export class PlannerModule {}
