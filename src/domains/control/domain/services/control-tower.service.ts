import { Inject, Injectable, Logger } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { AgentRun } from '../../../agent/infrastructure/persistence/agent-run.schema';
import {
  IDashboardMetrics,
  MetricsPeriod,
} from '../interfaces/dashboard-metrics.interface';
import {
  IToolExecutionRepository,
  TOOL_EXECUTION_REPOSITORY,
} from '../repositories/tool-execution.repository.interface';
import {
  IEvalRunRepository,
  EVAL_RUN_REPOSITORY,
} from '../../../evaluation/domain/repositories/eval-run.repository.interface';

@Injectable()
export class ControlTowerService {
  private readonly logger = new Logger(ControlTowerService.name);

  constructor(
    @InjectModel(AgentRun.name)
    private readonly agentRunModel: Model<InstanceType<typeof AgentRun>>,
    @Inject(TOOL_EXECUTION_REPOSITORY)
    private readonly toolExecutionRepo: IToolExecutionRepository,
    @Inject(EVAL_RUN_REPOSITORY)
    private readonly evalRunRepo: IEvalRunRepository,
  ) {}

  /**
   * Gera um snapshot de métricas operacionais do runtime.
   * Lê de agent_runs, tool_executions e eval_runs.
   */
  async getDashboard(period: MetricsPeriod = 'last_24h'): Promise<IDashboardMetrics> {
    const since = this.periodToDate(period);
    const generatedAt = new Date();

    // ── Agent runs aggregation ──────────────────────────────────────────────
    const [runStats, latencyStats] = await Promise.all([
      this.agentRunModel.aggregate<{ _id: string; count: number }>([
        { $match: { createdAt: { $gte: since } } },
        { $group: { _id: '$status', count: { $sum: 1 } } },
      ]),
      this.agentRunModel.aggregate<{
        avgLatencyMs: number;
        p95LatencyMs: number;
        totalTokens: number;
      }>([
        {
          $match: {
            status: 'completed',
            createdAt: { $gte: since },
          },
        },
        {
          $group: {
            _id: null,
            avgLatencyMs: { $avg: '$totalLatencyMs' },
            latencies: { $push: '$totalLatencyMs' },
            totalTokens: { $sum: '$totalTokens' },
          },
        },
      ]),
    ]);

    const runsByStatus: Record<string, number> = {};
    let totalRuns = 0;
    for (const stat of runStats) {
      runsByStatus[stat._id] = stat.count;
      totalRuns += stat.count;
    }

    const avgLatencyMs = latencyStats[0]?.avgLatencyMs ?? 0;
    const totalTokens = latencyStats[0]?.totalTokens ?? 0;
    const latencies: number[] = (latencyStats[0] as unknown as { latencies?: number[] })?.latencies ?? [];
    const p95LatencyMs = this.percentile(latencies, 95);

    // ── Runs by agent ──────────────────────────────────────────────────────
    const agentAgg = await this.agentRunModel.aggregate<{ _id: string; count: number }>([
      { $match: { createdAt: { $gte: since } } },
      {
        $addFields: {
          triggeredByAgent: {
            $cond: [{ $ne: ['$triggeredBy', null] }, '$triggeredBy', 'unknown'],
          },
        },
      },
      { $group: { _id: '$triggeredByAgent', count: { $sum: 1 } } },
    ]);
    const runsByAgent: Record<string, number> = {};
    for (const item of agentAgg) {
      runsByAgent[item._id] = item.count;
    }

    // ── Guardrail blocks ───────────────────────────────────────────────────
    const guardrailBlocks = await this.agentRunModel
      .countDocuments({
        createdAt: { $gte: since },
        'metadata.guardrailBlocked': true,
      })
      .exec();

    // ── Tool executions ────────────────────────────────────────────────────
    const [toolByStatus, topTools] = await Promise.all([
      this.toolExecutionRepo.countByStatusSince(since),
      this.toolExecutionRepo.topToolsSince(since, 5),
    ]);
    const totalToolExecutions = Object.values(toolByStatus).reduce((s, c) => s + c, 0);

    // ── Last eval score ────────────────────────────────────────────────────
    const recentEvals = await this.evalRunRepo.findRecent(1);
    const lastEvalScore = recentEvals[0]?.aggregateScore ?? null;

    this.logger.debug(
      `Dashboard gerado para período ${period}: ${totalRuns} runs, ${totalToolExecutions} tool executions`,
    );

    return {
      period,
      totalRuns,
      runsByStatus,
      avgLatencyMs: Math.round(avgLatencyMs),
      p95LatencyMs: Math.round(p95LatencyMs),
      totalTokens,
      runsByAgent,
      totalToolExecutions,
      toolExecutionsByStatus: toolByStatus,
      topTools,
      guardrailBlocks,
      lastEvalScore: lastEvalScore ?? null,
      generatedAt,
    };
  }

  private periodToDate(period: MetricsPeriod): Date {
    const now = Date.now();
    const map: Record<MetricsPeriod, number> = {
      last_1h: 60 * 60 * 1000,
      last_24h: 24 * 60 * 60 * 1000,
      last_7d: 7 * 24 * 60 * 60 * 1000,
      last_30d: 30 * 24 * 60 * 60 * 1000,
    };
    return new Date(now - map[period]);
  }

  private percentile(values: number[], p: number): number {
    if (values.length === 0) return 0;
    const sorted = [...values].sort((a, b) => a - b);
    const idx = Math.ceil((p / 100) * sorted.length) - 1;
    return sorted[Math.max(0, idx)];
  }
}
