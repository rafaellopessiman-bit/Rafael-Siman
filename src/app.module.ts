import { Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { ApiKeyGuard } from './shared/guards/api-key.guard';
import { ConfigModule } from './config/config.module';
import { DatabaseModule } from './database/database.module';
import { HealthModule } from './health/health.module';
import { KnowledgeModule } from './domains/knowledge/knowledge.module';
import { LlmModule } from './domains/llm/llm.module';
import { PlannerModule } from './domains/planner/planner.module';
import { TabularModule } from './domains/tabular/tabular.module';
import { AgentModule } from './domains/agent/agent.module';
import { EvaluationModule } from './domains/evaluation/evaluation.module';
import { ControlModule } from './domains/control/control.module';

@Module({
  imports: [
    ConfigModule,
    ThrottlerModule.forRoot([{ ttl: 60000, limit: 30 }]),
    DatabaseModule,
    HealthModule,
    KnowledgeModule,
    LlmModule,
    PlannerModule,
    TabularModule,
    AgentModule,
    EvaluationModule,
    ControlModule,
  ],
  providers: [
    { provide: APP_GUARD, useClass: ThrottlerGuard },
    { provide: APP_GUARD, useClass: ApiKeyGuard },
  ],
})
export class AppModule {}
