import { Controller, Get, Query } from '@nestjs/common';
import { ApiOperation, ApiQuery, ApiResponse, ApiTags } from '@nestjs/swagger';
import { Public } from '../../../../shared/guards/public.decorator';
import { ControlTowerService } from '../../domain/services/control-tower.service';
import { AlertService } from '../../domain/services/alert.service';
import { DashboardQueryDto } from '../../application/dto/dashboard-query.dto';
import { IDashboardMetrics } from '../../domain/interfaces/dashboard-metrics.interface';
import { IAlert } from '../../domain/interfaces/alert.interface';

@ApiTags('control')
@Controller('control')
@Public()
export class ControlController {
  constructor(
    private readonly controlTowerService: ControlTowerService,
    private readonly alertService: AlertService,
  ) {}

  @Get('dashboard')
  @ApiOperation({ summary: 'Retorna snapshot operacional do runtime agentic' })
  @ApiQuery({
    name: 'period',
    required: false,
    enum: ['last_1h', 'last_24h', 'last_7d', 'last_30d'],
  })
  @ApiResponse({ status: 200, description: 'Dashboard operacional' })
  async getDashboard(
    @Query() query: DashboardQueryDto,
  ): Promise<IDashboardMetrics> {
    return this.controlTowerService.getDashboard(query.period ?? 'last_24h');
  }

  @Get('health')
  @ApiOperation({ summary: 'Retorna saúde operacional e alertas ativos' })
  @ApiResponse({ status: 200, description: 'Health operacional do runtime' })
  async getHealth(): Promise<{
    status: 'healthy' | 'degraded' | 'critical';
    alerts: IAlert[];
    checkedAt: Date;
  }> {
    const alerts = await this.alertService.evaluate('last_1h');
    const status = alerts.some((a) => a.severity === 'critical')
      ? 'critical'
      : alerts.length > 0
        ? 'degraded'
        : 'healthy';

    return {
      status,
      alerts,
      checkedAt: new Date(),
    };
  }
}
