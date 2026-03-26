import { Controller, Get, Header, NotFoundException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import { Public } from '../guards/public.decorator';
import { MetricsService } from './metrics.service';

@ApiTags('telemetry')
@Controller()
export class TelemetryController {
  constructor(
    private readonly metricsService: MetricsService,
    private readonly configService: ConfigService,
  ) {}

  @Get('metrics')
  @Public()
  @SkipThrottle({ ask: true, act: true, extract: true })
  @Header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
  @ApiOperation({ summary: 'Expõe métricas Prometheus da aplicação' })
  async getMetrics(): Promise<string> {
    const metricsEnabled =
      this.configService.get<string>('METRICS_ENABLED', 'true') === 'true';

    if (!metricsEnabled) {
      throw new NotFoundException('Métricas desabilitadas');
    }

    return this.metricsService.getMetrics();
  }
}
