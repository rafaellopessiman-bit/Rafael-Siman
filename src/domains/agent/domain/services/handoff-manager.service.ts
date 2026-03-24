import { Injectable, Logger } from '@nestjs/common';
import { AgentRegistryService } from './agent-registry.service';
import { TracingService } from './tracing.service';
import {
  HandoffDecision,
  HandoffRecord,
} from '../interfaces/agent-handoff.interface';
import { AgentCapability } from '../interfaces/agent-capability.interface';

/** Palavras-chave que indicam intencao de busca documental. */
const KNOWLEDGE_KEYWORDS = [
  'quem', 'quando', 'onde', 'como', 'por que', 'qual', 'o que',
  'explique', 'descreva', 'resumo', 'sobre', 'informacao', 'informações',
  'documento', 'documentos', 'contrato', 'lei', 'artigo',
];

/** Palavras-chave que indicam intencao de extracao estruturada. */
const EXTRACTION_KEYWORDS = [
  'extraia', 'extrai', 'extrair', 'liste', 'listar', 'tabela', 'campos',
  'dados', 'estruturado', 'json', 'schema', 'parse', 'formato',
  'preencha', 'preencher',
];

/** Palavras-chave que indicam intencao de acao via tool. */
const TOOL_KEYWORDS = [
  'execute', 'fazer', 'realizar', 'acao', 'ative', 'chame', 'api',
  'envie', 'calcule',
];

/**
 * Gerencia decisoes e execucao de handoffs entre agentes.
 *
 * Responsabilidades:
 * - Analisar a intencao do usuario para decidir o agente inicial
 * - Validar se o handoff e permitido pela configuracao do agente
 * - Persistir o handoff como step no TracingService
 * - Detectar tokens [HANDOFF:agentId] na saida do agente
 */
@Injectable()
export class HandoffManagerService {
  private readonly logger = new Logger(HandoffManagerService.name);

  constructor(
    private readonly registry: AgentRegistryService,
    private readonly tracing: TracingService,
  ) {}

  /**
   * Decide qual agente deve tratar uma intencao inicial.
   * Usado pelo AgentOrchestratorService antes do primeiro loop.
   *
   * O supervisor faz a decisao final — este metodo e a heuristica
   * de roteamento rapido para casos claros, evitando chamar o LLM
   * so para rotear.
   */
  decide(userIntent: string, currentAgentId = 'supervisor_agent'): HandoffDecision {
    const intent = userIntent.toLowerCase();

    // Verifica se o agente atual pode fazer handoff (governanca)
    const current = this.registry.get(currentAgentId);
    if (!current || current.capabilities.includes(AgentCapability.ORCHESTRATION) === false) {
      // Agentes nao-supervisor nao fazem handoff heuristico, passam pro supervisor
      return {
        targetAgentId: 'supervisor_agent',
        reason: 'Agente nao-supervisor redirecionado ao supervisor',
        requiresContextInjection: false,
      };
    }

    if (this.matchesKeywords(intent, EXTRACTION_KEYWORDS)) {
      return {
        targetAgentId: 'extraction_agent',
        reason: 'Intencao de extracao estruturada detectada',
        requiresContextInjection: false,
      };
    }

    if (this.matchesKeywords(intent, TOOL_KEYWORDS)) {
      return {
        targetAgentId: 'tool_agent',
        reason: 'Intencao de execucao de acao detectada',
        requiresContextInjection: false,
      };
    }

    if (this.matchesKeywords(intent, KNOWLEDGE_KEYWORDS)) {
      return {
        targetAgentId: 'knowledge_agent',
        reason: 'Intencao de busca documental detectada',
        requiresContextInjection: true,
      };
    }

    // Default: knowledge agent para qualquer pergunta sobre documentos
    return {
      targetAgentId: 'knowledge_agent',
      reason: 'Roteamento padrao para busca documental',
      requiresContextInjection: true,
    };
  }

  /**
   * Detecta token de handoff na saida do agente.
   *
   * Formato esperado na saida: "[HANDOFF:agentId]"
   * Retorna null se nao ha solicitacao de handoff.
   */
  parseHandoffToken(agentOutput: string): string | null {
    const match = /\[HANDOFF:([a-z_]+)\]/.exec(agentOutput);
    return match ? match[1] : null;
  }

  /**
   * Valida e registra um handoff no TracingService.
   * Chamado pelo AgentOrchestratorService quando um handoff e detectado.
   */
  async execute(
    runId: string,
    stepNumber: number,
    record: Omit<HandoffRecord, 'timestamp'>,
  ): Promise<void> {
    const allowed = this.registry.isHandoffAllowed(record.fromAgentId, record.toAgentId);
    if (!allowed) {
      this.logger.warn(
        `Handoff BLOQUEADO: ${record.fromAgentId} → ${record.toAgentId} (nao esta em handoffTargets)`,
      );
      return;
    }

    await this.tracing.recordStep(runId, stepNumber, 'tool_call', {
      input: `handoff:${record.fromAgentId}→${record.toAgentId}`,
      output: record.reason,
      toolName: 'handoff',
      toolArgs: {
        fromAgentId: record.fromAgentId,
        toAgentId: record.toAgentId,
        reason: record.reason,
        contextSummary: record.contextSummary,
      },
    });

    this.logger.log(
      `Handoff executado: ${record.fromAgentId} → ${record.toAgentId} (${record.reason})`,
    );
  }

  private matchesKeywords(text: string, keywords: string[]): boolean {
    return keywords.some((kw) => text.includes(kw));
  }
}
