import { Module } from '@nestjs/common';
import { ConfigModule } from './config/config.module';
import { DatabaseModule } from './database/database.module';
import { HealthModule } from './health/health.module';
import { KnowledgeModule } from './domains/knowledge/knowledge.module';
import { LlmModule } from './domains/llm/llm.module';
import { PlannerModule } from './domains/planner/planner.module';
import { TabularModule } from './domains/tabular/tabular.module';

@Module({
  imports: [
    ConfigModule,
    DatabaseModule,
    HealthModule,
    KnowledgeModule,
    LlmModule,
    PlannerModule,
    TabularModule,
  ],
})
export class AppModule {}
