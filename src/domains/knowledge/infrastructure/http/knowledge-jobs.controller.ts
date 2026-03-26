import {
  Controller,
  Get,
  NotFoundException,
  Param,
} from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import { ApiOperation, ApiParam, ApiTags } from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import { Public } from '../../../../shared/guards/public.decorator';
import { KNOWLEDGE_INDEX_QUEUE } from '../../../../shared/queue/queue.constants';

@ApiTags('knowledge')
@Controller('knowledge/jobs')
@Public()
@SkipThrottle({ ask: true, act: true, extract: true })
export class KnowledgeJobsController {
  constructor(
    @InjectQueue(KNOWLEDGE_INDEX_QUEUE)
    private readonly knowledgeQueue: Queue,
  ) {}

  @Get(':jobId')
  @ApiOperation({ summary: 'Consulta status de um job de indexação' })
  @ApiParam({ name: 'jobId', description: 'ID do job retornado pelo POST /knowledge/async' })
  async getJobStatus(@Param('jobId') jobId: string) {
    const job = await this.knowledgeQueue.getJob(jobId);

    if (!job) {
      throw new NotFoundException(`Job "${jobId}" não encontrado`);
    }

    return {
      id: String(job.id),
      name: job.name,
      state: await job.getState(),
      attemptsMade: job.attemptsMade,
      failedReason: job.failedReason ?? null,
      progress: job.progress ?? 0,
    };
  }
}
