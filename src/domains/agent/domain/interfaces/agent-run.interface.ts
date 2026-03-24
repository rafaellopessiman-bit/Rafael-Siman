/**
 * Interfaces de tracing para runs e steps do agente.
 *
 * Um AgentRun representa uma execução completa do agent loop.
 * Cada AgentStep é uma ação atômica dentro do run (chamada LLM, tool call, etc.).
 */

export type AgentRunStatus = 'running' | 'completed' | 'failed' | 'timeout';

export type AgentStepType =
  | 'llm_call'
  | 'tool_call'
  | 'tool_result'
  | 'guardrail_input'
  | 'guardrail_output'
  | 'context_truncation'
  | 'final_answer';

export interface CreateAgentRunData {
  conversationId: string;
  status: AgentRunStatus;
  triggeredBy: string;
  metadata?: Record<string, unknown>;
}

export interface FinalizeAgentRunData {
  status: AgentRunStatus;
  totalIterations: number;
  totalTokens: number;
  totalLatencyMs: number;
  toolsUsed: string[];
  finalAnswer?: string;
  errorMessage?: string;
}

export interface CreateAgentStepData {
  runId: string;
  stepNumber: number;
  type: AgentStepType;
  input?: string;
  output?: string;
  tokensUsed?: number;
  latencyMs?: number;
  toolName?: string;
  toolArgs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}
