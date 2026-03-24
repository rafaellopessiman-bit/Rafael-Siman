export const AGENT_MEMORY_REPOSITORY = Symbol('AGENT_MEMORY_REPOSITORY');

export interface AgentMemoryData {
  conversationId: string;
  agentId: string;
  summary: string;
  keyFacts: string[];
  runIds: string[];
}

/**
 * Interface de repositorio para memorias resumidas de agentes.
 *
 * O ConversationMemoryService e o unico consumidor deste repositorio.
 * Cada entrada e identificada unicamente por (conversationId + agentId).
 */
export interface IAgentMemoryRepository {
  /** Busca memoria de um agente em uma conversa especifica. */
  findByConversationAndAgent(
    conversationId: string,
    agentId: string,
  ): Promise<AgentMemoryData | null>;

  /**
   * Cria ou atualiza a memoria de um agente em uma conversa.
   * Usa upsert por (conversationId + agentId).
   */
  upsert(memory: AgentMemoryData): Promise<AgentMemoryData>;

  /**
   * Retorna as memorias mais recentes de uma conversa
   * independente do agente, ordenadas por updatedAt desc.
   */
  findRecent(conversationId: string, limit?: number): Promise<AgentMemoryData[]>;
}
