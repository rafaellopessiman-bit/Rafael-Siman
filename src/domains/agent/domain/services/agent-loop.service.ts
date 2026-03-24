import { Injectable, Logger } from '@nestjs/common';
import { ToolRegistryService } from './tool-registry.service';
import { TracingService } from './tracing.service';
import { ContextManagerService } from './context-manager.service';
import { GuardrailPipelineService } from './guardrail-pipeline.service';
import {
  GroqClientService,
  GroqMessage,
} from '../../../llm/infrastructure/groq/groq-client.service';

const DEFAULT_SYSTEM_PROMPT = `Você é um agente inteligente de análise de documentos.

Você tem acesso a ferramentas (tools) que permitem buscar documentos, listar fontes e consultar cache.
Use as ferramentas quando precisar de informação da base de conhecimento.

Regras:
1. SEMPRE use a ferramenta search_documents antes de responder perguntas sobre conteúdo de documentos.
2. Se não encontrar informação suficiente, diga explicitamente.
3. Cite as fontes usadas na resposta.
4. Responda em português. Seja conciso e preciso.
5. Você pode encadear múltiplas chamadas de ferramentas se necessário.`;

const MAX_ITERATIONS = 8;

export interface AgentLoopResult {
  answer: string;
  toolsUsed: string[];
  iterations: number;
  totalTokens: number;
  latencyMs: number;
  runId?: string;
}

export interface AgentLoopOptions {
  conversationId?: string;
  triggeredBy?: string;
  /**
   * Lista de nomes de tools permitidas para este run.
   * Se fornecida, apenas estas tools sao enviadas ao LLM.
   * Usada pelo AgentOrchestratorService para enforcar whitelists por agente.
   */
  allowedToolNames?: string[];
}

/**
 * Orquestra o loop ReAct do agente:
 *
 *  1. Guardrail de input na mensagem do usuário
 *  2. Context management (truncation + summarization)
 *  3. Envia ao LLM com definições de tools
 *  4. Se LLM retorna tool_calls → executa tools em paralelo → injeta resultados
 *  5. Repete até LLM retornar resposta final (content sem tool_calls)
 *  6. Guardrail de output na resposta final
 *  7. Tracing completo de cada step no MongoDB
 *  8. Limite de segurança: MAX_ITERATIONS
 */
@Injectable()
export class AgentLoopService {
  private readonly logger = new Logger(AgentLoopService.name);

  constructor(
    private readonly toolRegistry: ToolRegistryService,
    private readonly groqClient: GroqClientService,
    private readonly tracing: TracingService,
    private readonly contextManager: ContextManagerService,
    private readonly guardrails: GuardrailPipelineService,
  ) {}

  async run(
    conversationMessages: GroqMessage[],
    systemPrompt?: string,
    options?: AgentLoopOptions,
  ): Promise<AgentLoopResult> {
    const startMs = Date.now();
    const allTools = this.toolRegistry.toGroqTools();
    // Aplica whitelist se fornecida pelo AgentOrchestratorService
    const tools = options?.allowedToolNames
      ? allTools.filter((t) => options.allowedToolNames!.includes(t.function.name))
      : allTools;
    const toolsUsed: string[] = [];
    let totalTokens = 0;
    let stepCounter = 0;

    // ── Tracing: inicia run ──
    const runId = await this.tracing.startRun(
      options?.conversationId ?? 'anonymous',
      options?.triggeredBy ?? 'api',
    );

    try {
      // ── Guardrail de input ──
      const lastUserMsg = conversationMessages
        .filter((m) => m.role === 'user')
        .pop();
      if (lastUserMsg?.content) {
        const inputCheck = await this.guardrails.runInput(lastUserMsg.content);
        await this.tracing.recordStep(runId, ++stepCounter, 'guardrail_input', {
          input: lastUserMsg.content,
          output: inputCheck.passed ? 'passed' : `blocked: ${inputCheck.reason}`,
        });
        if (!inputCheck.passed) {
          const blockedAnswer = inputCheck.reason ?? 'Mensagem bloqueada por guardrail de segurança.';
          await this.tracing.finalizeRun(runId, 'completed', {
            totalIterations: 0,
            totalTokens: 0,
            totalLatencyMs: Date.now() - startMs,
            toolsUsed: [],
            finalAnswer: blockedAnswer,
          });
          return {
            answer: blockedAnswer,
            toolsUsed: [],
            iterations: 0,
            totalTokens: 0,
            latencyMs: Date.now() - startMs,
            runId,
          };
        }
      }

      // ── Context management: trunca se necessário ──
      const managed = this.contextManager.prepare(
        conversationMessages,
        systemPrompt || DEFAULT_SYSTEM_PROMPT,
      );

      if (managed.truncated) {
        await this.tracing.recordStep(runId, ++stepCounter, 'context_truncation', {
          input: `${conversationMessages.length} mensagens`,
          output: `${managed.messages.length} mensagens (${managed.estimatedTokens} tokens estimados)`,
        });
      }

      // Monta mensagens iniciais
      const messages: GroqMessage[] = [
        { role: 'system', content: managed.systemPrompt },
        ...managed.messages,
      ];

      for (let iteration = 1; iteration <= MAX_ITERATIONS; iteration++) {
        this.logger.log(`Agent loop [run=${runId}] — iteração ${iteration}/${MAX_ITERATIONS}`);

        const llmStartMs = Date.now();
        const result = await this.groqClient.chatCompletionWithTools(
          messages,
          tools,
        );
        const llmLatency = Date.now() - llmStartMs;
        totalTokens += result.tokensUsed;

        // ── Tracing: LLM call ──
        await this.tracing.recordStep(runId, ++stepCounter, 'llm_call', {
          input: `iteration=${iteration}, messages=${messages.length}`,
          output: result.toolCalls?.length
            ? `${result.toolCalls.length} tool_calls`
            : result.content.substring(0, 200),
          tokensUsed: result.tokensUsed,
          latencyMs: llmLatency,
        });

        // Sem tool calls → resposta final
        if (!result.toolCalls || result.toolCalls.length === 0) {
          // ── Guardrail de output ──
          const outputCheck = await this.guardrails.runOutput(result.content);
          await this.tracing.recordStep(runId, ++stepCounter, 'guardrail_output', {
            input: result.content.substring(0, 200),
            output: outputCheck.passed ? 'passed' : `blocked: ${outputCheck.reason}`,
          });

          const finalAnswer = outputCheck.passed
            ? result.content
            : (outputCheck.modified ?? 'Resposta filtrada por guardrail de segurança.');

          await this.tracing.recordStep(runId, ++stepCounter, 'final_answer', {
            output: finalAnswer.substring(0, 500),
            tokensUsed: totalTokens,
            latencyMs: Date.now() - startMs,
          });

          await this.tracing.finalizeRun(runId, 'completed', {
            totalIterations: iteration,
            totalTokens,
            totalLatencyMs: Date.now() - startMs,
            toolsUsed: [...new Set(toolsUsed)],
            finalAnswer,
          });

          return {
            answer: finalAnswer,
            toolsUsed: [...new Set(toolsUsed)],
            iterations: iteration,
            totalTokens,
            latencyMs: Date.now() - startMs,
            runId,
          };
        }

        // Adiciona a resposta do assistente (com tool_calls) ao histórico
        messages.push({
          role: 'assistant',
          content: result.content,
          tool_calls: result.toolCalls,
        });

        // ── Executa tools em paralelo ──
        const toolPromises = result.toolCalls.map(async (toolCall) => {
          const toolName = toolCall.function.name;
          toolsUsed.push(toolName);

          let args: Record<string, unknown>;
          try {
            args = JSON.parse(toolCall.function.arguments);
          } catch {
            args = {};
            this.logger.warn(
              `Falha ao parsear argumentos da tool "${toolName}": ${toolCall.function.arguments}`,
            );
          }

          this.logger.log(
            `Executando tool "${toolName}" com params: ${JSON.stringify(args)}`,
          );

          const toolStartMs = Date.now();
          const toolResult = await this.toolRegistry.dispatch(toolName, args);
          const toolLatency = Date.now() - toolStartMs;

          // ── Tracing: tool_call ──
          await this.tracing.recordStep(runId, ++stepCounter, 'tool_call', {
            input: JSON.stringify(args).substring(0, 500),
            output: toolResult.substring(0, 500),
            toolName,
            toolArgs: args,
            latencyMs: toolLatency,
          });

          return { toolCall, result: toolResult };
        });

        const toolResults = await Promise.all(toolPromises);

        // Injeta resultados na ordem
        for (const { toolCall, result: toolResult } of toolResults) {
          messages.push({
            role: 'tool',
            content: toolResult,
            tool_call_id: toolCall.id,
          });
        }
      }

      // Atingiu limite de iterações — força resposta final
      this.logger.warn(
        `Agent loop [run=${runId}] atingiu limite de ${MAX_ITERATIONS} iterações`,
      );

      const finalResult = await this.groqClient.chatCompletion(messages);
      totalTokens += finalResult.tokensUsed;

      await this.tracing.finalizeRun(runId, 'timeout', {
        totalIterations: MAX_ITERATIONS,
        totalTokens,
        totalLatencyMs: Date.now() - startMs,
        toolsUsed: [...new Set(toolsUsed)],
        finalAnswer: finalResult.content,
      });

      return {
        answer: finalResult.content,
        toolsUsed: [...new Set(toolsUsed)],
        iterations: MAX_ITERATIONS,
        totalTokens,
        latencyMs: Date.now() - startMs,
        runId,
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      await this.tracing.finalizeRun(runId, 'failed', {
        totalIterations: 0,
        totalTokens,
        totalLatencyMs: Date.now() - startMs,
        toolsUsed: [...new Set(toolsUsed)],
        errorMessage: errorMsg,
      });
      throw error;
    }
  }
}
