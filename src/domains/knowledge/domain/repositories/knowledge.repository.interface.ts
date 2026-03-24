import { KnowledgeDocumentDocument } from '../../infrastructure/persistence/knowledge-document.schema';
import { KnowledgeDocument } from '../../infrastructure/persistence/knowledge-document.schema';

export const KNOWLEDGE_REPOSITORY = Symbol('KNOWLEDGE_REPOSITORY');

export type CreateKnowledgeDocumentData = Pick<
  KnowledgeDocument,
  'sourceFile' | 'content'
> &
  Partial<Pick<KnowledgeDocument, 'fileType' | 'chunkIndex' | 'metadata'>>;

export interface IKnowledgeRepository {
  create(doc: CreateKnowledgeDocumentData): Promise<KnowledgeDocumentDocument>;
  findBySourceFile(sourceFile: string): Promise<KnowledgeDocumentDocument[]>;
  searchText(query: string, limit: number): Promise<KnowledgeDocumentDocument[]>;
  deleteBySourceFile(sourceFile: string): Promise<number>;
}
