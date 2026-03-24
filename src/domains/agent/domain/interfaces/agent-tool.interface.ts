/**
 * Contrato de uma ferramenta (tool) que o agente IA pode invocar.
 *
 * Cada tool é auto-descritiva: nome, descrição e parâmetros são
 * enviados ao LLM no formato OpenAI-compatible {@link toFunctionSchema}.
 */
export interface IAgentTool {
  /** Identificador único (snake_case). Ex: "search_documents" */
  readonly name: string;

  /** Descrição curta que o LLM lê para decidir quando invocar. */
  readonly description: string;

  /** JSON Schema dos parâmetros aceitos. */
  readonly parameters: ToolParametersSchema;

  /** Executa a ferramenta e retorna resultado textual para o LLM. */
  execute(params: Record<string, unknown>): Promise<string>;
}

export interface ToolParameterDef {
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description: string;
  required?: boolean;
  default?: unknown;
}

export interface ToolParametersSchema {
  type: 'object';
  properties: Record<string, ToolParameterDef>;
  required: string[];
}

/** Formato OpenAI-compatible para enviar ao Groq. */
export interface GroqToolDefinition {
  type: 'function';
  function: {
    name: string;
    description: string;
    parameters: {
      type: 'object';
      properties: Record<string, { type: string; description: string }>;
      required: string[];
    };
  };
}

export const AGENT_TOOL_REGISTRY = Symbol('AGENT_TOOL_REGISTRY');
