import { Module } from '@nestjs/common';
import { ScheduleModule } from '@nestjs/schedule';
import { MongooseModule } from '@nestjs/mongoose';
import { CleanupService } from './cleanup.service';
import { QueryLog, QueryLogSchema } from '../../domains/llm/infrastructure/persistence/query-log.schema';

@Module({
  imports: [
    ScheduleModule.forRoot(),
    MongooseModule.forFeature([
      { name: QueryLog.name, schema: QueryLogSchema },
    ]),
  ],
  providers: [CleanupService],
})
export class SchedulerModule {}
