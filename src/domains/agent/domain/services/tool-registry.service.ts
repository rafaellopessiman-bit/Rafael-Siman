import { Injectable, Logger } from '@nestjs/common';
import {
  IAgentTool,
  GroqToolDefinition,
} from '../interfaces/agent-tool.interface';

/**
 * Registro central de tools disponíveis para o agente.
 *
 * Tools se auto-registram via {@link register} no onModuleInit de cada provider.
 * O AgentLoopService consulta o registry para:
 *  1. Gerar as definições de tools para o LLM
 *  2. Despachar chamadas de tool pelo nome
 */
@Injectable()
export class ToolRegistryService {
  private readonly logger = new Logger(ToolRegistryService.name);
  private readonly tools = new Map<string, IAgentTool>();

  register(tool: IAgentTool): void {
    if (this.tools.has(tool.name)) {
      this.logger.warn(`Tool "${tool.name}" já registrada — sobrescrevendo`);
    }
    this.tools.set(tool.name, tool);
    this.logger.log(`Tool registrada: ${tool.name}`);
  }

  get(name: string): IAgentTool | undefined {
    return this.tools.get(name);
  }

  getAll(): IAgentTool[] {
    return [...this.tools.values()];
  }

  /** Gera array de tool definitions no formato OpenAI/Groq. */
  toGroqTools(): GroqToolDefinition[] {
    return this.getAll().map((tool) => ({
      type: 'function' as const,
      function: {
        name: tool.name,
        description: tool.description,
        parameters: {
          type: 'object' as const,
          properties: Object.fromEntries(
            Object.entries(tool.parameters.properties).map(([key, def]) => [
              key,
              { type: def.type, description: def.description },
            ]),
          ),
          required: tool.parameters.required,
        },
      },
    }));
  }

  /** Despacha execução de tool pelo nome. */
  async dispatch(
    toolName: string,
    params: Record<string, unknown>,
  ): Promise<string> {
    const tool = this.tools.get(toolName);
    if (!tool) {
      return `[Erro] Tool "${toolName}" não encontrada no registry.`;
    }
    try {
      return await tool.execute(params);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      this.logger.error(`Tool "${toolName}" falhou: ${msg}`);
      return `[Erro ao executar "${toolName}"] ${msg}`;
    }
  }
}
