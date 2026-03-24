export { KnowledgeModule } from './knowledge.module';
export { IndexDocumentDto } from './application/dtos/index-document.dto';
export { SearchQueryDto } from './application/dtos/search-query.dto';
export { IndexDocumentUseCase } from './application/use-cases/index-document.use-case';
export { SearchDocumentsUseCase } from './application/use-cases/search-documents.use-case';
export { DeleteDocumentUseCase } from './application/use-cases/delete-document.use-case';
export { FindBySourceFileUseCase } from './application/use-cases/find-by-source-file.use-case';
export {
  KNOWLEDGE_REPOSITORY,
  type IKnowledgeRepository,
} from './domain/repositories/knowledge.repository.interface';
export {
  KnowledgeDocument,
  type KnowledgeDocumentDocument,
} from './infrastructure/persistence/knowledge-document.schema';
export { MongooseKnowledgeRepository } from './infrastructure/persistence/knowledge.repository';
export { KnowledgeController } from './infrastructure/http/knowledge.controller';
