import { IsIn, IsOptional } from 'class-validator';
import { ApiPropertyOptional } from '@nestjs/swagger';
import { MetricsPeriod } from '../../domain/interfaces/dashboard-metrics.interface';

export class DashboardQueryDto {
  @ApiPropertyOptional({
    enum: ['last_1h', 'last_24h', 'last_7d', 'last_30d'],
    description: 'Período de análise (default: last_24h)',
  })
  @IsOptional()
  @IsIn(['last_1h', 'last_24h', 'last_7d', 'last_30d'])
  period?: MetricsPeriod;
}
