import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { LlmCache, LlmCacheSchema } from './infrastructure/persistence/llm-cache.schema';
import { QueryLog, QueryLogSchema } from './infrastructure/persistence/query-log.schema';
import { MongooseLlmCacheRepository } from './infrastructure/persistence/llm-cache.repository';
import { MongooseQueryLogRepository } from './infrastructure/persistence/query-log.repository';
import { LLM_CACHE_REPOSITORY } from './domain/repositories/llm-cache.repository.interface';
import { QUERY_LOG_REPOSITORY } from './domain/repositories/query-log.repository.interface';
import { GetCachedResponseUseCase } from './application/use-cases/get-cached-response.use-case';
import { QueryLlmUseCase } from './application/use-cases/query-llm.use-case';
import { AskDocumentsUseCase } from './application/use-cases/ask-documents.use-case';
import { AskStreamUseCase } from './application/use-cases/ask-stream.use-case';
import { GroqClientService } from './infrastructure/groq/groq-client.service';
import { LlmController } from './infrastructure/http/llm.controller';
import { KnowledgeModule } from '../knowledge/knowledge.module';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: LlmCache.name, schema: LlmCacheSchema },
      { name: QueryLog.name, schema: QueryLogSchema },
    ]),
    KnowledgeModule,
  ],
  controllers: [LlmController],
  providers: [
    {
      provide: LLM_CACHE_REPOSITORY,
      useClass: MongooseLlmCacheRepository,
    },
    {
      provide: QUERY_LOG_REPOSITORY,
      useClass: MongooseQueryLogRepository,
    },
    GetCachedResponseUseCase,
    QueryLlmUseCase,
    AskDocumentsUseCase,
    AskStreamUseCase,
    GroqClientService,
  ],
  exports: [
    LLM_CACHE_REPOSITORY,
    QUERY_LOG_REPOSITORY,
    GroqClientService,
    AskDocumentsUseCase,
    AskStreamUseCase,
  ],
})
export class LlmModule {}
