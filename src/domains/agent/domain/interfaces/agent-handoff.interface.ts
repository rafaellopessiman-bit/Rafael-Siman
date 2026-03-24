/**
 * Contratos de handoff entre agentes no runtime multiagente.
 *
 * Um handoff e a transferencia explicita de controle de um agente para outro,
 * com contexto resumido e rastreamento via TracingService.
 */
export interface IAgentHandoff {
  /** ID do agente que esta transferindo o controle. */
  fromAgentId: string;

  /** ID do agente que recebe o controle. */
  toAgentId: string;

  /** Justificativa legivel para o handoff. */
  reason: string;

  /** Resumo do contexto relevante para o agente receptor. */
  contextSummary: string;

  /** Timestamp do handoff. */
  timestamp: Date;
}

/**
 * Decisao de handoff retornada pelo HandoffManagerService.
 * Ainda nao executada — apenas a intencao de transferir controle.
 */
export interface HandoffDecision {
  /** ID do agente que deve receber o controle. */
  targetAgentId: string;

  /** Justificativa da decisao de handoff. */
  reason: string;

  /**
   * Se true, o HandoffManager deve injetar um resumo de memoria
   * no system prompt do agente receptor antes de iniciar o loop.
   */
  requiresContextInjection: boolean;
}

/** Resultado de um handoff executado (persiste no TracingService). */
export interface HandoffRecord extends IAgentHandoff {
  runId: string;
  stepNumber: number;
}
