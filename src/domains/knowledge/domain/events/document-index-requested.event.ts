import { FileType } from '@/domains/shared/enums';

export const DOCUMENT_INDEX_REQUESTED = 'document.index.requested';

export interface DocumentIndexRequestedPayload {
  jobId: string;
  sourceFile: string;
  content: string;
  fileType?: FileType;
  chunkIndex?: number;
  metadata?: Record<string, unknown>;
  requestedAt: Date;
}
