/**
 * Audit log de uma execução de tool por um agente.
 *
 * Registrado pelo TracingService a cada tool_call+tool_result,
 * consumido pelo ControlTowerService para dashboard e alertas.
 */
export interface IToolExecution {
  id: string;

  /** ID do agent_run que originou esta execução. */
  runId: string;

  /** ID do agent_step associado (tool_call). */
  stepId: string;

  /** Identificador do agente que invocou a tool. */
  agentId: string;

  /** Nome registrado da tool (ex: "search_documents"). */
  toolName: string;

  /** Argumentos passados para a tool (snapshot). */
  toolArgs: Record<string, unknown>;

  /** Status da execução. */
  status: ToolExecutionStatus;

  /** Resultado retornado pela tool (truncado se necessário). */
  result?: string;

  /** Mensagem de erro caso status = "error". */
  errorMessage?: string;

  /** Latência da execução em milissegundos. */
  latencyMs: number;

  /** Timestamp de início UTC. */
  executedAt: Date;

  schemaVersion: number;
}

export type ToolExecutionStatus = 'success' | 'error' | 'timeout' | 'blocked';

export type CreateToolExecutionData = Omit<IToolExecution, 'id' | 'schemaVersion'>;
