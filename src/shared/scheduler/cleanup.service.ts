import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { QueryLog } from '../../domains/llm/infrastructure/persistence/query-log.schema';

@Injectable()
export class CleanupService {
  private readonly logger = new Logger(CleanupService.name);

  /** Retenção de query logs: 30 dias */
  private readonly queryLogRetentionDays = 30;

  constructor(
    @InjectModel(QueryLog.name) private readonly queryLogModel: Model<QueryLog>,
  ) {}

  /**
   * Daily at 03:00 — remove query logs mais antigos que o período de retenção.
   * O cache LLM já tem TTL index no MongoDB (24h), não precisa de limpeza manual.
   */
  @Cron(CronExpression.EVERY_DAY_AT_3AM, { name: 'cleanup-old-query-logs' })
  async cleanupOldQueryLogs(): Promise<void> {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - this.queryLogRetentionDays);

    const result = await this.queryLogModel.deleteMany({
      createdAt: { $lt: cutoff },
    });

    if (result.deletedCount > 0) {
      this.logger.log(
        `Cleaned ${result.deletedCount} query logs older than ${this.queryLogRetentionDays} days`,
      );
    }
  }
}
