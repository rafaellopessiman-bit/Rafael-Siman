import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { BullModule } from '@nestjs/bullmq';
import { KNOWLEDGE_INDEX_QUEUE } from '../../shared/queue/queue.constants';
import { TelemetryModule } from '../../shared/telemetry/telemetry.module';
import { DocumentIndexListener } from './infrastructure/listeners/document-index.listener';
import { KnowledgeIndexProcessor } from './infrastructure/queue/knowledge-index.processor';
import { KnowledgeJobsController } from './infrastructure/http/knowledge-jobs.controller';
import { EnqueueKnowledgeIndexUseCase } from './application/use-cases/enqueue-knowledge-index.use-case';
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
import { ChunkingService } from './domain/services/chunking.service';
import {
  EMBEDDING_SERVICE,
  EmbeddingService,
} from './domain/services/embedding.service';

const useBullMQ = process.env.INDEX_ASYNC_DRIVER === 'bullmq';

const bullImports = useBullMQ
  ? [BullModule.registerQueue({ name: KNOWLEDGE_INDEX_QUEUE })]
  : [];

const bullControllers = useBullMQ ? [KnowledgeJobsController] : [];
const bullProviders = useBullMQ ? [KnowledgeIndexProcessor] : [];

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: KnowledgeDocument.name, schema: KnowledgeDocumentSchema },
    ]),
    TelemetryModule,
    ...bullImports,
  ],
  controllers: [KnowledgeController, ...bullControllers],
  providers: [
    {
      provide: KNOWLEDGE_REPOSITORY,
      useClass: MongooseKnowledgeRepository,
    },
    {
      provide: EMBEDDING_SERVICE,
      useClass: EmbeddingService,
    },
    ChunkingService,
    IndexDocumentUseCase,
    SearchDocumentsUseCase,
    DeleteDocumentUseCase,
    FindBySourceFileUseCase,
    EnqueueKnowledgeIndexUseCase,
    DocumentIndexListener,
    ...bullProviders,
  ],
  exports: [KNOWLEDGE_REPOSITORY, EMBEDDING_SERVICE, ChunkingService],
})
export class KnowledgeModule {}
