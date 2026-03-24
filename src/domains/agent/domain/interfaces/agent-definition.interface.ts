import { AgentCapability } from './agent-capability.interface';

/**
 * Definicao formal e versionada de um agente no registry.
 *
 * Cada agente tem identidade propria, capacidades declaradas,
 * lista aprovada de tools e destinos possiveis de handoff.
 * O sistema nao permite que um agente use tools fora de allowedTools.
 */
export interface IAgentDefinition {
  /** Identificador unico (snake_case). Ex: "knowledge_agent". */
  id: string;

  /** Nome legivel para humanos. */
  name: string;

  /** Descricao do proposito e comportamento esperado. */
  description: string;

  /** Versao semantica da definicao. Ex: "1.0.0". */
  version: string;

  /** Capacidades declaradas pelo agente. */
  capabilities: AgentCapability[];

  /**
   * Tools que este agente tem permissao de invocar.
   * O AgentOrchestratorService filtra o ToolRegistry por esta lista
   * antes de passar tools para o loop do agente.
   */
  allowedTools: string[];

  /**
   * IDs de agentes para os quais este agente pode fazer handoff.
   * O HandoffManagerService valida esta lista antes de executar handoff.
   */
  handoffTargets: string[];

  /**
   * System prompt especifico deste agente.
   * Substitui o prompt padrao do AgentLoopService.
   */
  systemPrompt: string;

  /** Se false, o agente nao e carregado no registry. */
  isActive: boolean;
}

/** Dados usados para criar ou atualizar uma definicao no MongoDB. */
export type CreateAgentDefinitionData = Omit<IAgentDefinition, never>;
