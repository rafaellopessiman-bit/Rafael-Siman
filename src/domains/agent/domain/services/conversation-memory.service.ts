import { Injectable, Inject, Logger } from '@nestjs/common';
import {
  AGENT_MEMORY_REPOSITORY,
  IAgentMemoryRepository,
  AgentMemoryData,
} from '../repositories/agent-memory.repository.interface';

const MAX_KEY_FACTS = 20;
const MAX_SUMMARY_CHARS = 500;

/**
 * Gerencia memoria resumida de longo prazo por (conversa × agente).
 *
 * Diferenca do ContextManagerService:
 * - ContextManagerService trata o context window DO RUN ATUAL (short-term)
 * - ConversationMemoryService trata memoria ENTRE RUNS (long-term)
 *
 * A memoria e injetada como contexto adicional no system prompt
 * do agente especialista antes de iniciar um novo run.
 */
@Injectable()
export class ConversationMemoryService {
  private readonly logger = new Logger(ConversationMemoryService.name);

  constructor(
    @Inject(AGENT_MEMORY_REPOSITORY)
    private readonly repo: IAgentMemoryRepository,
  ) {}

  /** Recupera a memoria atual de um agente em uma conversa. */
  async getMemory(
    conversationId: string,
    agentId: string,
  ): Promise<AgentMemoryData | null> {
    return this.repo.findByConversationAndAgent(conversationId, agentId);
  }

  /**
   * Atualiza a memoria apos um run concluido.
   *
   * Estrategia de atualizacao:
   * - Adiciona novos fatos-chave sem duplicatas
   * - Mantem lista em no maximo MAX_KEY_FACTS itens (FIFO)
   * - Atualiza o resumo textual se fornecido
   */
  async updateMemory(
    conversationId: string,
    agentId: string,
    newFacts: string[],
    runId: string,
    newSummary?: string,
  ): Promise<void> {
    const existing = await this.repo.findByConversationAndAgent(
      conversationId,
      agentId,
    );

    const existingFacts = existing?.keyFacts ?? [];
    const existingRunIds = existing?.runIds ?? [];

    // Deduplica e limita key facts
    const mergedFacts = [
      ...new Set([...existingFacts, ...newFacts]),
    ].slice(-MAX_KEY_FACTS);

    const mergedRunIds = [...new Set([...existingRunIds, runId])];

    const summary = newSummary
      ? newSummary.slice(0, MAX_SUMMARY_CHARS)
      : (existing?.summary ?? '');

    await this.repo.upsert({
      conversationId,
      agentId,
      summary,
      keyFacts: mergedFacts,
      runIds: mergedRunIds,
    });

    this.logger.debug(
      `Memoria atualizada: conversa=${conversationId} agente=${agentId} fatos=${mergedFacts.length}`,
    );
  }

  /**
   * Constroi o bloco de contexto de memoria para injecao no system prompt.
   *
   * Retorna string vazia se nao ha memoria previa.
   * O retorno e incluido pelo AgentOrchestratorService no system prompt
   * do agente especialista como secao "## Contexto de execucoes anteriores".
   */
  async buildContextBlock(
    conversationId: string,
    agentId: string,
  ): Promise<string> {
    const memory = await this.repo.findByConversationAndAgent(
      conversationId,
      agentId,
    );

    if (!memory || (memory.keyFacts.length === 0 && !memory.summary)) {
      return '';
    }

    const parts: string[] = ['## Contexto de execucoes anteriores'];

    if (memory.summary) {
      parts.push(`Resumo: ${memory.summary}`);
    }

    if (memory.keyFacts.length > 0) {
      parts.push('Fatos relevantes:');
      memory.keyFacts.forEach((f) => parts.push(`- ${f}`));
    }

    return parts.join('\n');
  }

  /** Retorna memorias recentes de todos os agentes de uma conversa. */
  async getRecentMemories(
    conversationId: string,
    limit = 5,
  ): Promise<AgentMemoryData[]> {
    return this.repo.findRecent(conversationId, limit);
  }
}
