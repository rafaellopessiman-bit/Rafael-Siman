import { Injectable, Logger } from '@nestjs/common';
import { OnEvent } from '@nestjs/event-emitter';
import { IndexDocumentUseCase } from '../../application/use-cases/index-document.use-case';
import {
  DOCUMENT_INDEX_REQUESTED,
  DocumentIndexRequestedPayload,
} from '../../domain/events/document-index-requested.event';

@Injectable()
export class DocumentIndexListener {
  private readonly logger = new Logger(DocumentIndexListener.name);

  constructor(private readonly indexDocument: IndexDocumentUseCase) {}

  @OnEvent(DOCUMENT_INDEX_REQUESTED)
  async handleIndexRequest(payload: DocumentIndexRequestedPayload): Promise<void> {
    const start = Date.now();
    this.logger.log(`[${payload.jobId}] Indexação async iniciada: ${payload.sourceFile}`);

    try {
      const docs = await this.indexDocument.execute({
        sourceFile: payload.sourceFile,
        content: payload.content,
        fileType: payload.fileType,
        chunkIndex: payload.chunkIndex,
        metadata: payload.metadata,
      });

      const latencyMs = Date.now() - start;
      this.logger.log(
        `[${payload.jobId}] Indexação async completa: ${docs.length} chunks em ${latencyMs}ms`,
      );
    } catch (error) {
      const latencyMs = Date.now() - start;
      this.logger.error(
        `[${payload.jobId}] Indexação async falhou em ${latencyMs}ms`,
        error instanceof Error ? error.stack : String(error),
      );
    }
  }
}
