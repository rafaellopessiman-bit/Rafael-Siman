import { IEvalScore } from '../../../evaluation/domain/interfaces/eval-score.interface';

/**
 * Snapshot de métricas operacionais do runtime agentic.
 * Retornado pelo endpoint GET /control/dashboard.
 */
export interface IDashboardMetrics {
  /** Período analisado. */
  period: MetricsPeriod;

  /** Total de agent_runs no período. */
  totalRuns: number;

  /** Runs por status. */
  runsByStatus: Record<string, number>;

  /** Latência média dos runs completados (ms). */
  avgLatencyMs: number;

  /** Latência p95 dos runs completados (ms). */
  p95LatencyMs: number;

  /** Total de tokens consumidos. */
  totalTokens: number;

  /** Runs por agente (agentId → count). */
  runsByAgent: Record<string, number>;

  /** Contagem de tool executions no período. */
  totalToolExecutions: number;

  /** Tool executions por status. */
  toolExecutionsByStatus: Record<string, number>;

  /** Top 5 tools mais invocadas. */
  topTools: Array<{ toolName: string; count: number }>;

  /** Guardrail blocks no período. */
  guardrailBlocks: number;

  /** Último eval score agregado (null se nenhum eval run existir). */
  lastEvalScore: IEvalScore | null;

  /** Timestamp da geração do snapshot. */
  generatedAt: Date;
}

export type MetricsPeriod = 'last_1h' | 'last_24h' | 'last_7d' | 'last_30d';
