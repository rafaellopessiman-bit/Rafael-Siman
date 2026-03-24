import { BadRequestException, Inject, Injectable } from '@nestjs/common';
import { randomUUID } from 'crypto';
import {
  TOOL_EXECUTION_REPOSITORY,
  IToolExecutionRepository,
} from '../../../control/domain/repositories/tool-execution.repository.interface';
import { ToolRegistryService } from '../../domain/services/tool-registry.service';
import { ActDto, ActResponse } from '../dtos/act.dto';
import { SUPPORTED_ACTIONS } from '../../infrastructure/tools/execute-whitelisted-action.tool';

@Injectable()
export class ExecuteGovernedActionUseCase {
  constructor(
    private readonly toolRegistry: ToolRegistryService,
    @Inject(TOOL_EXECUTION_REPOSITORY)
    private readonly toolExecutionRepository: IToolExecutionRepository,
  ) {}

  async execute(dto: ActDto): Promise<ActResponse> {
    this.ensureSupportedAllowedActions(dto.allowedActions);

    const action = this.selectAction(dto.intent, dto.allowedActions);
    const runId = randomUUID();
    const stepId = randomUUID();
    const executedAt = new Date();
    const startMs = Date.now();
    const result = await this.toolRegistry.dispatch('execute_whitelisted_action', {
      action,
      intent: dto.intent,
      contextId: dto.contextId,
    });
    const latencyMs = Date.now() - startMs;
    const status = result.startsWith('[Erro') ? 'error' as const : 'success' as const;
    const resultData = this.tryParseResult(result);

    await this.toolExecutionRepository.create({
      runId,
      stepId,
      agentId: 'tool_agent',
      toolName: 'execute_whitelisted_action',
      toolArgs: {
        action,
        intent: dto.intent,
        contextId: dto.contextId,
        allowedActions: dto.allowedActions,
      },
      status,
      result: status === 'success' ? result : undefined,
      errorMessage: status === 'error' ? result : undefined,
      latencyMs,
      executedAt,
    });

    return {
      runId,
      toolName: 'execute_whitelisted_action',
      action,
      mode: resultData?.mode === 'dry_run' ? 'dry_run' as const : 'live' as const,
      status,
      audited: true,
      result,
      resultData: resultData ?? undefined,
      executedAt,
      latencyMs,
    };
  }

  private selectAction(intent: string, allowedActions: string[]): string {
    if (allowedActions.length === 1) {
      return allowedActions[0];
    }

    const normalizedIntent = this.normalize(intent);
    const rankedActions = allowedActions
      .map((action) => ({
        action,
        score: this.scoreActionMatch(normalizedIntent, this.normalize(action)),
      }))
      .sort((left, right) => right.score - left.score);

    const matchedAction = rankedActions[0]?.score > 0 ? rankedActions[0].action : undefined;

    if (!matchedAction) {
      throw new BadRequestException(
        'Nenhuma acao governada compativel com a intent informada.',
      );
    }

    return matchedAction;
  }

  private normalize(value: string): string {
    return value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  }

  private ensureSupportedAllowedActions(allowedActions: string[]): void {
    const unsupported = allowedActions.filter((action) => !SUPPORTED_ACTIONS.has(action));

    if (unsupported.length > 0) {
      throw new BadRequestException(
        `AllowedActions contem itens nao suportados: ${unsupported.join(', ')}`,
      );
    }
  }

  private scoreActionMatch(normalizedIntent: string, normalizedAction: string): number {
    if (!normalizedIntent || !normalizedAction) {
      return 0;
    }

    if (normalizedIntent.includes(normalizedAction)) {
      return normalizedAction.length + 5;
    }

    const actionTokens = normalizedAction.split(' ').filter(Boolean);
    const intentTokens = new Set(normalizedIntent.split(' ').filter(Boolean));
    return actionTokens.reduce((score, token) => score + (intentTokens.has(token) ? 1 : 0), 0);
  }

  private tryParseResult(result: string): Record<string, unknown> | null {
    try {
      return JSON.parse(result) as Record<string, unknown>;
    } catch {
      return null;
    }
  }
}
