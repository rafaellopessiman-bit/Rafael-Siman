import { Logger } from '@nestjs/common';
import { Processor, WorkerHost } from '@nestjs/bullmq';
import type { Job } from 'bullmq';
import { IndexDocumentUseCase } from '../../application/use-cases/index-document.use-case';
import type { IndexDocumentDto } from '../../application/dtos/index-document.dto';
import { KNOWLEDGE_INDEX_QUEUE } from '../../../../shared/queue/queue.constants';

@Processor(KNOWLEDGE_INDEX_QUEUE)
export class KnowledgeIndexProcessor extends WorkerHost {
  private readonly logger = new Logger(KnowledgeIndexProcessor.name);

  constructor(
    private readonly indexDocumentUseCase: IndexDocumentUseCase,
  ) {
    super();
  }

  async process(job: Job<IndexDocumentDto>) {
    this.logger.log(`Job ${job.id} iniciado para ${job.data.sourceFile}`);

    try {
      const result = await this.indexDocumentUseCase.execute(job.data);

      let chunkCount = 0;
      let failedChunkCount = 0;

      // Tenta inferir contagem de chunks e falhas parciais de forma resiliente ao formato de retorno
      if (Array.isArray(result)) {
        chunkCount = result.length;
        failedChunkCount = result.filter(
          (chunk: any) => chunk && (chunk.error || chunk.failed === true),
        ).length;
      } else if (result && typeof result === 'object') {
        const anyResult: any = result;

        if (Array.isArray(anyResult.chunks)) {
          chunkCount = anyResult.chunks.length;
        }

        if (Array.isArray(anyResult.failedChunks)) {
          failedChunkCount = anyResult.failedChunks.length;
        }
      }

      if (failedChunkCount > 0) {
        this.logger.warn(
          `Job ${job.id} concluído com falhas parciais: ${failedChunkCount} chunks falharam de um total de ${chunkCount}`,
        );
      } else {
        this.logger.log(
          `Job ${job.id} concluído com ${chunkCount} chunks`,
        );
      }

      return {
        chunkCount,
        failedChunkCount,
        sourceFile: job.data.sourceFile,
      };
    } catch (error) {
      this.logger.error(
        `Job ${job.id} falhou ao indexar ${job.data.sourceFile}`,
        (error as Error)?.stack,
      );
      throw error;
    }
  }
}
