/**
 * Configuração de alerta por threshold.
 * O AlertService monitora esses limiares e gera alertas.
 */
export interface IAlertRule {
  id: string;

  /** Nome legível do alerta. */
  name: string;

  /** Métrica monitorada. */
  metric: AlertMetric;

  /** Operador de comparação. */
  operator: AlertOperator;

  /** Valor limite. */
  threshold: number;

  /** Janela de tempo para avaliação (minutos). */
  windowMinutes: number;

  /** Se a regra está ativa. */
  isActive: boolean;

  schemaVersion: number;
}

export type AlertMetric =
  | 'avg_latency_ms'
  | 'p95_latency_ms'
  | 'guardrail_block_rate'
  | 'error_rate'
  | 'tool_error_rate'
  | 'eval_overall_score';

export type AlertOperator = 'gt' | 'gte' | 'lt' | 'lte';

/**
 * Alerta disparado quando uma regra é violada.
 */
export interface IAlert {
  id: string;
  ruleId: string;
  ruleName: string;
  metric: AlertMetric;
  currentValue: number;
  threshold: number;
  severity: AlertSeverity;
  message: string;
  triggeredAt: Date;
  acknowledgedAt?: Date;
}

export type AlertSeverity = 'info' | 'warning' | 'critical';
