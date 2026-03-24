import {
  DocumentIndex,
  DocumentIndexDocument,
} from '../../infrastructure/persistence/document-index.schema';

export const DOCUMENT_INDEX_REPOSITORY = Symbol('DOCUMENT_INDEX_REPOSITORY');

export type UpsertDocumentIndexData = Partial<
  Pick<DocumentIndex, 'status' | 'fileHash' | 'chunkCount' | 'totalChars' | 'lastIndexedAt' | 'errorMessage'>
>;

export interface IDocumentIndexRepository {
  upsertIndex(sourceFile: string, data: UpsertDocumentIndexData): Promise<DocumentIndexDocument>;
  findPending(): Promise<DocumentIndexDocument[]>;
  findAll(): Promise<DocumentIndexDocument[]>;
}
