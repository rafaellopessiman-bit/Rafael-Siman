import { Injectable, Inject, Logger } from '@nestjs/common';
import {
  AGENT_RUN_REPOSITORY,
  IAgentRunRepository,
} from '../repositories/agent-run.repository.interface';
import {
  AGENT_STEP_REPOSITORY,
  IAgentStepRepository,
} from '../repositories/agent-step.repository.interface';
import {
  AgentRunStatus,
  AgentStepType,
} from '../interfaces/agent-run.interface';

/**
 * Serviço de tracing para execuções do agente.
 *
 * Registra cada run (execução completa) e cada step (ação atômica)
 * no MongoDB para observabilidade, debug e métricas.
 */
@Injectable()
export class TracingService {
  private readonly logger = new Logger(TracingService.name);

  constructor(
    @Inject(AGENT_RUN_REPOSITORY)
    private readonly runRepo: IAgentRunRepository,
    @Inject(AGENT_STEP_REPOSITORY)
    private readonly stepRepo: IAgentStepRepository,
  ) {}

  /** Cria um novo run e retorna o ID. */
  async startRun(
    conversationId: string,
    triggeredBy: string,
  ): Promise<string> {
    const run = await this.runRepo.create({
      conversationId,
      status: 'running',
      triggeredBy,
    });
    this.logger.log(`Run iniciado: ${run._id} (conversa: ${conversationId})`);
    return run._id.toString();
  }

  /** Registra uma step atômica dentro de um run. */
  async recordStep(
    runId: string,
    stepNumber: number,
    type: AgentStepType,
    data: {
      input?: string;
      output?: string;
      tokensUsed?: number;
      latencyMs?: number;
      toolName?: string;
      toolArgs?: Record<string, unknown>;
    },
  ): Promise<void> {
    await this.stepRepo.create({
      runId,
      stepNumber,
      type,
      ...data,
    });
  }

  /** Finaliza um run com o resultado. */
  async finalizeRun(
    runId: string,
    status: AgentRunStatus,
    data: {
      totalIterations: number;
      totalTokens: number;
      totalLatencyMs: number;
      toolsUsed: string[];
      finalAnswer?: string;
      errorMessage?: string;
    },
  ): Promise<void> {
    await this.runRepo.finalize(runId, { status, ...data });
    this.logger.log(
      `Run finalizado: ${runId} (status: ${status}, iterations: ${data.totalIterations}, tokens: ${data.totalTokens})`,
    );
  }

  /** Recupera um run pelo ID. */
  async getRun(runId: string) {
    return this.runRepo.findById(runId);
  }

  /** Recupera steps de um run. */
  async getSteps(runId: string) {
    return this.stepRepo.findByRun(runId);
  }

  /** Lista runs recentes. */
  async getRecentRuns(limit = 20, skip = 0) {
    return this.runRepo.findRecent(limit, skip);
  }

  /** Conta total de runs. */
  async countRecentRuns() {
    return this.runRepo.countRecent();
  }

  /** Lista runs de uma conversa. */
  async getRunsByConversation(conversationId: string, limit = 20, skip = 0) {
    return this.runRepo.findByConversation(conversationId, limit, skip);
  }

  /** Conta runs de uma conversa. */
  async countRunsByConversation(conversationId: string) {
    return this.runRepo.countByConversation(conversationId);
  }
}
