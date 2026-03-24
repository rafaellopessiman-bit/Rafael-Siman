import { Inject, Injectable, Logger } from '@nestjs/common';
import {
  IAlertRule,
  IAlert,
  AlertSeverity,
} from '../interfaces/alert.interface';
import {
  IAlertRuleRepository,
  ALERT_RULE_REPOSITORY,
} from '../repositories/alert-rule.repository.interface';
import { ControlTowerService } from './control-tower.service';
import { MetricsPeriod } from '../interfaces/dashboard-metrics.interface';
import { randomUUID } from 'crypto';

/**
 * Serviço de alertas por threshold.
 *
 * Avalia regras configuradas contra métricas do ControlTowerService.
 * Retorna alertas ativos sem persistência de estado (stateless por design).
 */
@Injectable()
export class AlertService {
  private readonly logger = new Logger(AlertService.name);

  /** Regras padrão carregadas no startup. */
  private static readonly DEFAULT_RULES: IAlertRule[] = [
    {
      id: 'avg-latency-warning',
      name: 'Latência média > 10s',
      metric: 'avg_latency_ms',
      operator: 'gt',
      threshold: 10_000,
      windowMinutes: 60,
      isActive: true,
      schemaVersion: 1,
    },
    {
      id: 'p95-latency-critical',
      name: 'P95 latência > 30s',
      metric: 'p95_latency_ms',
      operator: 'gt',
      threshold: 30_000,
      windowMinutes: 60,
      isActive: true,
      schemaVersion: 1,
    },
    {
      id: 'error-rate-warning',
      name: 'Taxa de erro > 20%',
      metric: 'error_rate',
      operator: 'gt',
      threshold: 0.20,
      windowMinutes: 60,
      isActive: true,
      schemaVersion: 1,
    },
    {
      id: 'eval-score-critical',
      name: 'Eval score < 0.5',
      metric: 'eval_overall_score',
      operator: 'lt',
      threshold: 0.5,
      windowMinutes: 1440, // 24h
      isActive: true,
      schemaVersion: 1,
    },
  ];

  constructor(
    @Inject(ALERT_RULE_REPOSITORY)
    private readonly ruleRepo: IAlertRuleRepository,
    private readonly controlTower: ControlTowerService,
  ) {}

  /**
   * Avalia todas as regras ativas e retorna alertas disparados.
   */
  async evaluate(period: MetricsPeriod = 'last_1h'): Promise<IAlert[]> {
    const [rules, dashboard] = await Promise.all([
      this.ruleRepo.findActive(),
      this.controlTower.getDashboard(period),
    ]);

    const alerts: IAlert[] = [];

    for (const rule of rules) {
      const value = this.extractMetricValue(rule.metric, dashboard, rules);
      if (value === null) continue;

      const violated = this.checkThreshold(value, rule.operator, rule.threshold);
      if (!violated) continue;

      const severity = this.determineSeverity(rule.metric, value, rule.threshold);
      alerts.push({
        id: randomUUID(),
        ruleId: rule.id,
        ruleName: rule.name,
        metric: rule.metric,
        currentValue: value,
        threshold: rule.threshold,
        severity,
        message: `[${severity.toUpperCase()}] ${rule.name}: ${value.toFixed(2)} ${rule.operator} ${rule.threshold}`,
        triggeredAt: new Date(),
      });

      this.logger.warn(
        `Alerta disparado: ${rule.name} (${rule.metric}=${value.toFixed(2)})`,
      );
    }

    return alerts;
  }

  /** Garante que as regras padrão existem (idempotente). */
  async seedDefaultRules(): Promise<void> {
    for (const rule of AlertService.DEFAULT_RULES) {
      await this.ruleRepo.upsert(rule);
    }
    this.logger.log(`${AlertService.DEFAULT_RULES.length} regras de alerta padrão garantidas`);
  }

  private extractMetricValue(
    metric: IAlertRule['metric'],
    dashboard: Awaited<ReturnType<ControlTowerService['getDashboard']>>,
    _rules: IAlertRule[],
  ): number | null {
    switch (metric) {
      case 'avg_latency_ms':
        return dashboard.avgLatencyMs;
      case 'p95_latency_ms':
        return dashboard.p95LatencyMs;
      case 'guardrail_block_rate':
        return dashboard.totalRuns > 0
          ? dashboard.guardrailBlocks / dashboard.totalRuns
          : 0;
      case 'error_rate': {
        const failed = dashboard.runsByStatus['failed'] ?? 0;
        return dashboard.totalRuns > 0 ? failed / dashboard.totalRuns : 0;
      }
      case 'tool_error_rate': {
        const toolTotal = dashboard.totalToolExecutions;
        const toolErrors = dashboard.toolExecutionsByStatus['error'] ?? 0;
        return toolTotal > 0 ? toolErrors / toolTotal : 0;
      }
      case 'eval_overall_score':
        return dashboard.lastEvalScore?.overallScore ?? null;
      default:
        return null;
    }
  }

  private checkThreshold(
    value: number,
    operator: IAlertRule['operator'],
    threshold: number,
  ): boolean {
    switch (operator) {
      case 'gt': return value > threshold;
      case 'gte': return value >= threshold;
      case 'lt': return value < threshold;
      case 'lte': return value <= threshold;
    }
  }

  private determineSeverity(
    metric: IAlertRule['metric'],
    value: number,
    threshold: number,
  ): AlertSeverity {
    if (metric === 'eval_overall_score' && value < 0.3) return 'critical';
    if (metric === 'p95_latency_ms' && value > threshold * 1.5) return 'critical';
    if (metric === 'error_rate' && value > 0.4) return 'critical';
    if (value > threshold * 2) return 'critical';
    if (value > threshold * 1.2) return 'warning';
    return 'info';
  }
}
