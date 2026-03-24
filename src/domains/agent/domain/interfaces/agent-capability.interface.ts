/**
 * Capabilities formais que um agente pode declarar.
 *
 * Usadas pelo HandoffManagerService para rotear intenções do usuário
 * para o agente especialista correto e pelo AgentRegistryService
 * para introspeccao do runtime.
 */
export enum AgentCapability {
  /** Agente pode recuperar e citar conteudo da base de conhecimento. */
  KNOWLEDGE_RETRIEVAL = 'knowledge_retrieval',

  /** Agente pode extrair dados estruturados seguindo um schema. */
  STRUCTURED_EXTRACTION = 'structured_extraction',

  /** Agente pode executar acoes via tools externas aprovadas. */
  TOOL_EXECUTION = 'tool_execution',

  /** Agente pode revisar e criticar o output de outros agentes. */
  CONTENT_CRITIQUE = 'content_critique',

  /** Agente pode orquestrar outros agentes e decidir handoffs. */
  ORCHESTRATION = 'orchestration',
}

export type AgentCapabilitySet = Set<AgentCapability>;
