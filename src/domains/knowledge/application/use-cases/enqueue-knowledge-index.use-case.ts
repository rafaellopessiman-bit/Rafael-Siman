import { Injectable, Logger, Optional } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { EventEmitter2 } from '@nestjs/event-emitter';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import { randomUUID } from 'crypto';
import { IndexDocumentDto } from '../dtos/index-document.dto';
import {
  DOCUMENT_INDEX_REQUESTED,
  type DocumentIndexRequestedPayload,
} from '../../domain/events/document-index-requested.event';
import {
  KNOWLEDGE_INDEX_JOB,
  KNOWLEDGE_INDEX_QUEUE,
} from '../../../../shared/queue/queue.constants';

@Injectable()
export class EnqueueKnowledgeIndexUseCase {
  private readonly logger = new Logger(EnqueueKnowledgeIndexUseCase.name);

  constructor(
    private readonly configService: ConfigService,
    private readonly eventEmitter: EventEmitter2,
    @Optional()
    @InjectQueue(KNOWLEDGE_INDEX_QUEUE)
    private readonly knowledgeQueue?: Queue<IndexDocumentDto>,
  ) {}

  async execute(dto: IndexDocumentDto) {
    const driver = this.configService.get<string>(
      'INDEX_ASYNC_DRIVER',
      'event_emitter',
    );

    if (driver === 'bullmq') {
      if (!this.knowledgeQueue) {
        throw new Error('BullMQ driver selected but Redis queue is not available');
      }
      const job = await this.knowledgeQueue.add(KNOWLEDGE_INDEX_JOB, dto, {
        attempts: 5,
        backoff: { type: 'exponential', delay: 2000 },
        removeOnComplete: 1000,
        removeOnFail: 5000,
      });

      this.logger.log(
        `[bullmq] Job ${job.id} enfileirado para ${dto.sourceFile}`,
      );

      return { jobId: String(job.id), status: 'accepted', driver: 'bullmq' };
    }

    // Fallback: EventEmitter em memória (S10)
    const jobId = randomUUID();
    const payload: DocumentIndexRequestedPayload = {
      jobId,
      sourceFile: dto.sourceFile,
      content: dto.content,
      fileType: dto.fileType,
      chunkIndex: dto.chunkIndex,
      metadata: dto.metadata,
      requestedAt: new Date(),
    };

    this.eventEmitter.emit(DOCUMENT_INDEX_REQUESTED, payload);
    this.logger.log(
      `[event_emitter] Job ${jobId} emitido para ${dto.sourceFile}`,
    );

    return { jobId, status: 'accepted', driver: 'event_emitter' };
  }
}
