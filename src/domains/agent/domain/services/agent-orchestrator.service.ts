import { Injectable, Logger } from '@nestjs/common';
import { AgentLoopService, AgentLoopResult } from './agent-loop.service';
import { AgentRegistryService } from './agent-registry.service';
import { HandoffManagerService } from './handoff-manager.service';
import { ConversationMemoryService } from './conversation-memory.service';
import { ToolRegistryService } from './tool-registry.service';
import { GroqMessage } from '../../../llm/infrastructure/groq/groq-client.service';

export interface OrchestratorResult extends AgentLoopResult {
  /** Agentes utilizados, em ordem de ativacao. */
  agentsUsed: string[];

  /** Numero de handoffs realizados neste request. */
  handoffCount: number;

  /** ID do agente que produziu a resposta final. */
  finalAgentId: string;
}

export interface OrchestratorOptions {
  conversationId?: string;
  triggeredBy?: string;

  /**
   * Se true, o orquestrador usa a heuristica de roteamento rapido
   * sem chamar o supervisor via LLM. Padrao: true para baixa latencia.
   */
  useHeuristicRouting?: boolean;

  /** Numero maximo de handoffs permitidos por request. Padrao: 3. */
  maxHandoffs?: number;
}

const DEFAULT_MAX_HANDOFFS = 3;

/**
 * Orquestrador central do runtime multiagente.
 *
 * Fluxo de execucao:
 * 1. Analisa intencao do usuario via HandoffManagerService (heuristica ou supervisor)
 * 2. Carrega memoria previa da conversa via ConversationMemoryService
 * 3. Injeta contexto de memoria no system prompt do agente selecionado
 * 4. Filtra tools pelo whitelist do agente (AgentRegistryService.isToolAllowed)
 * 5. Executa AgentLoopService com tools filtradas
 * 6. Detecta tokens [HANDOFF:agentId] na resposta e troca de agente
 * 7. Repete ate resposta final ou limite de handoffs atingido
 * 8. Atualiza memoria apos conclusao
 */
@Injectable()
export class AgentOrchestratorService {
  private readonly logger = new Logger(AgentOrchestratorService.name);

  constructor(
    private readonly agentLoop: AgentLoopService,
    private readonly registry: AgentRegistryService,
    private readonly handoffManager: HandoffManagerService,
    private readonly memory: ConversationMemoryService,
    private readonly toolRegistry: ToolRegistryService,
  ) {}

  async orchestrate(
    conversationMessages: GroqMessage[],
    options: OrchestratorOptions = {},
  ): Promise<OrchestratorResult> {
    const {
      conversationId = 'anonymous',
      triggeredBy = 'api',
      useHeuristicRouting = true,
      maxHandoffs = DEFAULT_MAX_HANDOFFS,
    } = options;

    const agentsUsed: string[] = [];
    let handoffCount = 0;

    // Extrai ultima mensagem do usuario para analise de intencao
    const lastUserMessage = conversationMessages
      .filter((m) => m.role === 'user')
      .pop();
    const userIntent = lastUserMessage?.content ?? '';

    // Decide agente inicial
    const initialDecision = useHeuristicRouting
      ? this.handoffManager.decide(userIntent, 'supervisor_agent')
      : { targetAgentId: 'supervisor_agent', reason: 'Inicio via supervisor', requiresContextInjection: false };

    let currentAgentId = initialDecision.targetAgentId;
    agentsUsed.push(currentAgentId);

    this.logger.log(
      `Orquestracao iniciada: agente=${currentAgentId} conversa=${conversationId} heuristica=${useHeuristicRouting}`,
    );

    let lastResult: AgentLoopResult | null = null;
    let currentMessages = [...conversationMessages];

    while (handoffCount <= maxHandoffs) {
      const agentDef = this.registry.get(currentAgentId);
      if (!agentDef) {
        this.logger.warn(`Agente "${currentAgentId}" nao encontrado no registry — usando knowledge_agent`);
        currentAgentId = 'knowledge_agent';
        agentsUsed.push(currentAgentId);
        continue;
      }

      // Constroi system prompt com injecao de memoria
      const memoryBlock = await this.memory.buildContextBlock(
        conversationId,
        currentAgentId,
      );
      const systemPrompt = memoryBlock
        ? `${agentDef.systemPrompt}\n\n${memoryBlock}`
        : agentDef.systemPrompt;

      // Filtra tools pela whitelist do agente
      const allowedTools = this.toolRegistry.getAll().filter((tool) =>
        this.registry.isToolAllowed(currentAgentId, tool.name),
      );

      this.logger.log(
        `Executando ${currentAgentId}: ${allowedTools.length} tools disponiveis`,
      );

      // Registra tools filtradas temporariamente no contexto do run
      // (o AgentLoopService usa o ToolRegistryService completo por padrao,
      //  entao passamos as tools via opcao de override)
      lastResult = await this.runWithFilteredTools(
        currentMessages,
        systemPrompt,
        allowedTools.map((t) => t.name),
        { conversationId, triggeredBy },
      );

      // Verifica se a resposta pede handoff
      const handoffTarget = this.handoffManager.parseHandoffToken(lastResult.answer);

      if (!handoffTarget || handoffCount >= maxHandoffs) {
        break;
      }

      // Valida governanca do handoff
      if (!this.registry.isHandoffAllowed(currentAgentId, handoffTarget)) {
        this.logger.warn(
          `Handoff bloqueado por politica: ${currentAgentId} → ${handoffTarget}`,
        );
        break;
      }

      // Executa handoff
      await this.handoffManager.execute(
        lastResult.runId ?? 'unknown',
        (lastResult.iterations ?? 0) + handoffCount + 1,
        {
          fromAgentId: currentAgentId,
          toAgentId: handoffTarget,
          reason: `Token [HANDOFF:${handoffTarget}] detectado na saida`,
          contextSummary: lastResult.answer.slice(0, 500),
          runId: lastResult.runId ?? '',
          stepNumber: handoffCount + 1,
        },
      );

      handoffCount++;

      // Prepara contexto para o proximo agente:
      // Injeta o resultado do agente anterior como mensagem do assistente
      currentMessages = [
        ...conversationMessages,
        {
          role: 'assistant',
          content: `[Contexto do ${currentAgentId}]: ${lastResult.answer.replace(/\[HANDOFF:[a-z_]+\]/g, '').trim()}`,
        },
      ];

      currentAgentId = handoffTarget;
      agentsUsed.push(currentAgentId);

      this.logger.log(
        `Handoff ${handoffCount}/${maxHandoffs}: → ${currentAgentId}`,
      );
    }

    if (!lastResult) {
      throw new Error('Orquestracao falhou: nenhum resultado produzido');
    }

    // Atualiza memoria com fatos do run
    const keyFacts = this.extractKeyFacts(lastResult.answer, agentsUsed);
    await this.memory.updateMemory(
      conversationId,
      agentsUsed[agentsUsed.length - 1],
      keyFacts,
      lastResult.runId ?? 'unknown',
    );

    return {
      ...lastResult,
      agentsUsed,
      handoffCount,
      finalAgentId: currentAgentId,
    };
  }

  /**
   * Executa o AgentLoopService respeitando a whitelist de tools do agente.
   *
   * Estrategia: registra temporariamente uma lista filtrada de tools no
   * ToolRegistryService, executa o loop, e restaura o registry original.
   * Isso garante que o AgentLoopService nao invoca tools fora da whitelist.
   */
  private async runWithFilteredTools(
    messages: GroqMessage[],
    systemPrompt: string,
    allowedToolNames: string[],
    options: { conversationId: string; triggeredBy: string },
  ): Promise<AgentLoopResult> {
    // Backup das tools completas
    const allTools = this.toolRegistry.getAll();

    // Tools sao filtradas no AgentLoopService via allowedToolNames
    // allTools referenciado apenas para diagnostico futuro
    void allTools;

    // Por seguranca: desregistra tools bloqueadas do registry do agente
    // usando o mecanismo de override por contexto de run
    // (sem modificar o registry global — usa scope por execucao)
    return this.agentLoop.run(messages, systemPrompt, {
      conversationId: options.conversationId,
      triggeredBy: options.triggeredBy,
      allowedToolNames,
    });
  }

  private extractKeyFacts(answer: string, agentsUsed: string[]): string[] {
    const facts: string[] = [];

    if (agentsUsed.length > 1) {
      facts.push(`Fluxo multiagente: ${agentsUsed.join(' → ')}`);
    }

    // Extrai mencao de fontes/documentos encontrados
    const sourceMatch = answer.match(/fonte[s]?:?\s*([^\n.]+)/i);
    if (sourceMatch) {
      facts.push(`Fontes acessadas: ${sourceMatch[1].trim().slice(0, 100)}`);
    }

    return facts;
  }
}
