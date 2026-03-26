import { Controller, Get } from '@nestjs/common';
import {
  HealthCheck,
  HealthCheckService,
  MongooseHealthIndicator,
  DiskHealthIndicator,
  MemoryHealthIndicator,
} from '@nestjs/terminus';
import { ConfigService } from '@nestjs/config';
import { ApiTags, ApiOperation } from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import { Public } from '../shared/guards/public.decorator';

@ApiTags('health')
@Controller('health')
@Public()
@SkipThrottle({ default: true, ask: true, act: true, extract: true })
export class HealthController {
  private readonly heapThreshold: number;

  constructor(
    private health: HealthCheckService,
    private mongoose: MongooseHealthIndicator,
    private disk: DiskHealthIndicator,
    private memory: MemoryHealthIndicator,
    configService: ConfigService,
  ) {
    const mb = configService.get<number>('HEALTH_HEAP_THRESHOLD_MB') ?? 512;
    this.heapThreshold = mb * 1024 * 1024;
  }

  @Get()
  @HealthCheck()
  @ApiOperation({ summary: 'Health check — MongoDB connectivity' })
  check() {
    return this.health.check([
      () => this.mongoose.pingCheck('mongodb'),
    ]);
  }

  @Get('detailed')
  @HealthCheck()
  @ApiOperation({ summary: 'Health check detalhado — MongoDB + Disk + Heap' })
  detailed() {
    return this.health.check([
      () => this.mongoose.pingCheck('mongodb'),
      () => this.disk.checkStorage('disk', {
        path: process.platform === 'win32' ? 'C:\\' : '/',
        thresholdPercent: 0.9,
      }),
      () => this.memory.checkHeap('heap', this.heapThreshold),
    ]);
  }
}
