import { MiddlewareConsumer, Module, NestModule } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { ConfigService } from '@nestjs/config';
import { EventEmitterModule } from '@nestjs/event-emitter';
import { QueueModule } from './shared/queue/queue.module';
import { CacheModule } from './shared/cache/cache.module';
import { TelemetryModule } from './shared/telemetry/telemetry.module';
import { SchedulerModule } from './shared/scheduler/scheduler.module';
import { ApiKeyGuard } from './shared/guards/api-key.guard';
import { CorrelationIdMiddleware } from './shared/middleware/correlation-id.middleware';
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
    ThrottlerModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => [
        {
          name: 'default',
          ttl: cfg.get<number>('THROTTLE_TTL', 60000),
          limit: cfg.get<number>('THROTTLE_LIMIT', 30),
        },
        {
          name: 'ask',
          ttl: cfg.get<number>('THROTTLE_ASK_TTL', 60000),
          limit: cfg.get<number>('THROTTLE_ASK_LIMIT', 10),
        },
        {
          name: 'act',
          ttl: cfg.get<number>('THROTTLE_ACT_TTL', 60000),
          limit: cfg.get<number>('THROTTLE_ACT_LIMIT', 5),
        },
        {
          name: 'extract',
          ttl: cfg.get<number>('THROTTLE_EXTRACT_TTL', 60000),
          limit: cfg.get<number>('THROTTLE_EXTRACT_LIMIT', 10),
        },
      ],
    }),
    EventEmitterModule.forRoot(),
    QueueModule.register(),
    CacheModule,
    TelemetryModule,
    SchedulerModule,
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
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer.apply(CorrelationIdMiddleware).forRoutes('*');
  }
}
