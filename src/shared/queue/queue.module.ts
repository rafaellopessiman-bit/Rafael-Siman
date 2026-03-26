import { DynamicModule, Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { ConfigService } from '@nestjs/config';

@Module({})
export class QueueModule {
  static register(): DynamicModule {
    const useBullMQ = process.env.INDEX_ASYNC_DRIVER === 'bullmq';

    if (!useBullMQ) {
      return { module: QueueModule, global: true };
    }

    return {
      module: QueueModule,
      global: true,
      imports: [
        BullModule.forRootAsync({
          inject: [ConfigService],
          useFactory: (cfg: ConfigService) => ({
            connection: {
              host: cfg.get<string>('REDIS_HOST', 'localhost'),
              port: cfg.get<number>('REDIS_PORT', 6379),
            },
          }),
        }),
      ],
      exports: [BullModule],
    };
  }
}
