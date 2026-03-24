import { Inject, Injectable, OnModuleInit } from '@nestjs/common';
import {
  IAgentTool,
  ToolParametersSchema,
} from '../../domain/interfaces/agent-tool.interface';
import { ToolRegistryService } from '../../domain/services/tool-registry.service';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../../knowledge/domain/repositories/knowledge.repository.interface';
import {
  TOOL_EXECUTION_REPOSITORY,
  IToolExecutionRepository,
} from '../../../control/domain/repositories/tool-execution.repository.interface';

export const SUPPORTED_ACTIONS = new Set([
  'refresh_sources_index',
  'sync_control_metrics',
  'preview_external_lookup',
]);

@Injectable()
export class ExecuteWhitelistedActionTool implements IAgentTool, OnModuleInit {
  readonly name = 'execute_whitelisted_action';
  readonly description =
    'Executa uma acao governada aprovada pelo runtime com integracao real e resposta auditavel.';
  readonly parameters: ToolParametersSchema = {
    type: 'object',
    properties: {
      action: {
        type: 'string',
        description: 'Nome da acao governada a executar',
        required: true,
      },
      intent: {
        type: 'string',
        description: 'Intent original do usuario que motivou a acao',
      },
      contextId: {
        type: 'string',
        description: 'Identificador opcional do contexto de negocio associado',
      },
    },
    required: ['action'],
  };

  constructor(
    private readonly registry: ToolRegistryService,
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepository: IKnowledgeRepository,
    @Inject(TOOL_EXECUTION_REPOSITORY)
    private readonly toolExecutionRepository: IToolExecutionRepository,
  ) {}

  onModuleInit(): void {
    this.registry.register(this);
  }

  async execute(params: Record<string, unknown>): Promise<string> {
    const action = String(params.action ?? '').trim();
    const intent = params.intent ? String(params.intent) : undefined;
    const contextId = params.contextId ? String(params.contextId) : undefined;

    if (!action) {
      return '[Erro] Acao governada obrigatoria.';
    }

    if (!SUPPORTED_ACTIONS.has(action)) {
      return `[Erro] Acao governada "${action}" nao suportada.`;
    }

    const actionResult = await this.dispatchAction(action, intent);

    return JSON.stringify(
      {
        action,
        status: 'accepted',
        mode: 'live',
        contextId: contextId ?? null,
        summary: actionResult.summary,
        details: actionResult.details,
        executedAt: new Date().toISOString(),
      },
      null,
      2,
    );
  }

  private async dispatchAction(
    action: string,
    intent?: string,
  ): Promise<{ summary: string; details: Record<string, unknown> }> {
    switch (action) {
      case 'refresh_sources_index':
        return this.handleRefreshSourcesIndex();
      case 'sync_control_metrics':
        return this.handleSyncControlMetrics();
      case 'preview_external_lookup':
        return this.handlePreviewExternalLookup(intent);
      default:
        return {
          summary: 'Acao governada executada.',
          details: {},
        };
    }
  }

  private async handleRefreshSourcesIndex(): Promise<{
    summary: string;
    details: Record<string, unknown>;
  }> {
    const docs = await this.knowledgeRepository.searchText('', 10_000);
    const sourceFiles = [...new Set(docs.map((d) => String(d.sourceFile ?? '')))];

    return {
      summary: `Indice de fontes atualizado: ${sourceFiles.length} fonte(s), ${docs.length} chunk(s).`,
      details: {
        totalSources: sourceFiles.length,
        totalChunks: docs.length,
        sources: sourceFiles.slice(0, 50),
      },
    };
  }

  private async handleSyncControlMetrics(): Promise<{
    summary: string;
    details: Record<string, unknown>;
  }> {
    const since = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const [statusCounts, topTools] = await Promise.all([
      this.toolExecutionRepository.countByStatusSince(since),
      this.toolExecutionRepository.topToolsSince(since, 5),
    ]);

    const totalExecutions = Object.values(statusCounts).reduce((a, b) => a + b, 0);

    return {
      summary: `Metricas sincronizadas: ${totalExecutions} execucao(oes) nas ultimas 24h.`,
      details: {
        period: '24h',
        totalExecutions,
        statusBreakdown: statusCounts,
        topTools,
      },
    };
  }

  private async handlePreviewExternalLookup(intent?: string): Promise<{
    summary: string;
    details: Record<string, unknown>;
  }> {
    const query = intent ?? '';
    const previews = await this.knowledgeRepository.searchText(query, 5);
    const results = previews.map((doc) => ({
      sourceFile: doc.sourceFile,
      snippet: String(doc.content ?? '').slice(0, 200),
    }));

    return {
      summary: `Preview de lookup concluido: ${results.length} resultado(s) encontrado(s).`,
      details: {
        query,
        resultCount: results.length,
        results,
      },
    };
  }
}
