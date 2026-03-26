import { Module } from '@nestjs/common';
import { TelemetryController } from './telemetry.controller';
import { MetricsService } from './metrics.service';

@Module({
  providers: [MetricsService],
  controllers: [TelemetryController],
  exports: [MetricsService],
})
export class TelemetryModule {}
